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
from .models import Visitor,VisitorEventHistory
from django.utils import timezone
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Initialize Redis client
redis_client = redis.StrictRedis(host="redis", port=6379, db=0)
# @shared_task
def process_frame_task(bytes_data, group_name, camera_id, timestamp):
    start_time = time.time()
    try:
        # visitors=Visitor.objects.get.all()
        frame = bytes_data
        timestamp = int(timestamp)
        detected_time = timezone.now()

        candidates = Visitor.objects.filter(is_tracking_enabled=True, is_deleted=False, ml_attributes__isnull=False)
        if not candidates.exists():
            logger.info("🚫 No eligible visitors for auto detection.")
            return
        
        files = [
            ('frame', ("frame.jpg", frame, 'image/jpeg'))
        ]
        data = {
            'camera_id': camera_id,
        }
        response = requests.post("http://mlserver.com/detect", files=files, data=data)
        if response.status_code != 200:
            logger.error(f"❌ ML server error: {response.status_code} - {response.text}")
            raise RuntimeError("ML server failed")
        ml_attributes = response.json()
        logger.info(f"🧠 ML Attributes: {ml_attributes}")



        detected_embeddings = ml_attributes.get("ml_attributes", [])  # List of embedding arrays

        if not detected_embeddings:
            logger.info("🛑 No embeddings returned by ML server.")
            return
        
        matched_visitors = []
        threshold = 0.6  # Define an appropriate similarity threshold
        for embedding in detected_embeddings:
            for visitor in candidates:
                pass
            pass
        if not matched_visitors:
            logger.info("❌ No matching visitor found from embeddings.")
            return
      
        event = VisitorEventHistory.objects.create(
                visitor_ids=[],  # Temp empty; will update later
                camera_id=camera_id,
                snapshot_url="https://default.snapshot",#detected frame er url hobe
                capture_time=timestamp,
                detected_time=detected_time,
                ml_attributes=ml_attributes
            )
        event.visitors.set(matched_visitors)
    except Exception as e:
        logging.error(f"Error in process_frame_task: {str(e)}")
        # Optionally send error to WebSocket group
        channel_layer = get_channel_layer()
        asyncio.run(channel_layer.group_send(
            group_name,
            {
                'type': 'data_message',
                'data': {'error': f"Frame processing failed: {str(e)}"},
            }
        ))
