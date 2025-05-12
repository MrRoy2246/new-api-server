# your_app/tasks.py
import cv2
import numpy as np
import json
import time
import logging
import aiohttp
# from celery import shared_task
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.db import transaction
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
import redis
import asyncio
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Visitor,VisitorEventHistory,Camera
from django.utils import timezone
import requests
from .utils import get_minio_client
import uuid
from io import BytesIO


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Initialize Redis client
redis_client = redis.StrictRedis(host="redis", port=6379, db=0)
# @shared_task
def process_frame_task(bytes_data, group_name, camera_id, timestamp):
    # start_time = time.time()
    try:
        try:
            camera = Camera.objects.get(camera_id=camera_id)
        except Camera.DoesNotExist:
            logger.warning(f"🚫 Cannot create event — Camera ID {camera_id} not found in database.")
            return
        frame = bytes_data
        timestamp = int(timestamp)
        detected_time = timezone.now()
        candidates = Visitor.objects.filter(
            is_tracking_enabled=True,
            is_deleted=False,
            ml_attributes__isnull=False
        )
        if not candidates.exists():
            logger.info("🚫 No eligible visitors with tracking enabled.")
            return
        # STEP 2: Send frame to ML only if there are trackable visitors
        files = [
            ('frame', ("frame.jpg", frame, 'image/jpeg'))
        ]
        # data = {
        #     'camera_id': camera_id,
        # }
        print("testing print")
        response = requests.post("http://localhost:8000/api/mock-ml/", files=files)# data=data)
        if response.status_code != 200:
            logger.error(f"❌ ML server error: {response.status_code} - {response.text}")
            return
        ml_response = response.json()
        print(f"this is automatic ml response{ml_response}")
        logger.info(f"🧠 ML Response: {ml_response}")
        # detected_embeddings = ml_response.get("ml_attributes", [])
        attribute_dict = ml_response.get("ml_attributes", {})
        detected_embeddings = list(attribute_dict.values())
        if not detected_embeddings:
            logger.info("🛑 No embeddings returned by ML.")
            return
        matched_visitors = []
        threshold = 0.6  # You can tune this
        # for embedding in detected_embeddings:
        #     for visitor in candidates:
        #         stored = visitor.ml_attributes or []
        #         if len(stored) != len(embedding):
        #             continue
        #         # Simple similarity measure: ratio of matches
        #         match_ratio = sum([1 for i, j in zip(stored, embedding) if i == j]) / len(embedding)
        #         if match_ratio >= threshold:
        #             matched_visitors.append(visitor)
        for visitor in candidates:
            stored = visitor.ml_attributes or []
            if len(stored) != len(detected_embeddings):
                continue
            # Calculate the match ratio
            match_ratio = sum([1 for i, j in zip(stored, detected_embeddings) if i == j]) / len(detected_embeddings)
            if match_ratio >= threshold:
                matched_visitors.append(visitor)
        if not matched_visitors:
            logger.info("❌ No matching visitors found.")
            return
        s3 = get_minio_client()
        file_key = f"localtest/visitor_snapshots/{uuid.uuid4()}.jpg"
        try:
            s3.upload_fileobj(
                BytesIO(frame),  # Convert bytes to file-like object
                settings.AWS_STORAGE_BUCKET_NAME,
                file_key,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )
        except Exception as e:
            logger.error(f"📤 MinIO upload failed: {e}")
            return
        snapshot_url = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{file_key}"
        event = VisitorEventHistory.objects.create(
                visitor_ids=[],  # Temp empty; will update later
                camera_id=camera_id,
                snapshot_url=snapshot_url,#detected frame er url hobe
                capture_time=timestamp,
                detected_time=detected_time,
            )
        event.visitors.set(matched_visitors)
        logger.info(f"✅ Created event for matched visitors: {[v.id for v in matched_visitors]}")
    except Exception as e:
        logging.error(f"Error in process_frame_task: {str(e)}")
        # Optionally send error to WebSocket group
        group_name = "visitor_events"
        channel_layer = get_channel_layer()
        asyncio.run(channel_layer.group_send(
            group_name,
            {
                'type': 'notification.message',
                'message': {'error': f"Frame processing failed: {str(e)}"},
            }
        ))
