# myapp/utils.py
import boto3
from django.conf import settings

def get_minio_client():
    return boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

import threading

_thread_locals = threading.local()

def set_request_token(token):
    _thread_locals.token = token

def get_request_token():
    return getattr(_thread_locals, 'token', None)

def clear_request_token():
    _thread_locals.token = None




from dotenv import load_dotenv
load_dotenv(dotenv_path = r'C:\ABIN-Work\NewApiServer\NewApiServer\.env')
import redis.asyncio as redis
import os
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

camera_redis = redis.Redis(
    host=os.getenv("CAMERA_REDIS_HOST", "192.168.1.10"),
    port=int(os.getenv("CAMERA_REDIS_PORT", 6379)),
    db=0,
    decode_responses=False
)

async def get_latest_camera_frame(camera_id):
    """Asynchronously retrieve the latest camera frame from Redis."""
    zset_key = f"camera_frames:{camera_id}"
    try:
        start_time = asyncio.get_event_loop().time()

        # Use pipeline to reduce round-trips
        async with camera_redis.pipeline() as pipe:
            pipe.zrevrange(zset_key, 0, 0)  # Get the latest frame key
            latest_frame_key = (await pipe.execute())[0]
        
        logger.info(f"ZSET Key: {zset_key}")
        logger.info(f"Latest frame key raw: {latest_frame_key}")

        if latest_frame_key:
            latest_frame_key = latest_frame_key[0]
            logger.info(f"Latest frame key: {latest_frame_key}")
            if isinstance(latest_frame_key, bytes):
                latest_frame_key = latest_frame_key.decode()

            # Retrieve the image data
            frame_data = await camera_redis.get(latest_frame_key)
            if not frame_data:
                logger.error(f"No frame data found for {latest_frame_key}.")
                return None

            timestamp = int(latest_frame_key.split(":")[-1])
            logger.info(
                f"Retrieved frame for camera {camera_id}, "
                f"time: {asyncio.get_event_loop().time() - start_time:.2f}s"
            )

            return {
                "camera_id": camera_id,
                "timestamp": timestamp,
                "frame": frame_data
            }

        return None
    except Exception as e:
        logger.error(f"Error retrieving frame for camera {camera_id}: {e}")
        return None