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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Redis client
redis_client = redis.StrictRedis(host="redis", port=6379, db=0)

# @shared_task
def process_frame_task(bytes_data, group_name, camera_id, timestamp):
    start_time = time.time()
    try:


        frame = bytes_data
        print(f"this is test frame --------{frame}")
        timestamp = int(timestamp)
        detected_time = timezone.now()
        event = VisitorEventHistory.objects.create(
                visitor_ids=[],  # Temp empty; will update later
                camera_id=camera_id,
                snapshot_url="https://default.snapshot",
                capture_time=timestamp,
                detected_time=detected_time,
            )
        # event.visitors.set(visitors)


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
