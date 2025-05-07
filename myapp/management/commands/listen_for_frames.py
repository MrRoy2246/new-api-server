# camera/management/commands/listen_for_frames.py

import asyncio
import json
from django.core.management.base import BaseCommand
from myapp.utils import camera_redis, get_latest_camera_frame
from myapp.consumer_task import process_frame_task
import os
import logging
from dotenv import load_dotenv
load_dotenv(dotenv_path = r'C:\ABIN-Work\NewApiServer\NewApiServer\.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHANNEL_NAMES = os.getenv("CHANNEL_NAMES","274f0909-1551-4c8e-b1cb-c08166202b08").split(",")

class Command(BaseCommand):
    help = "Listen for camera frame events via Redis Pub/Sub asynchronously for multiple channels"

    async def process_message(self, message, channel_name):
        """Process a single Pub/Sub message in a separate task."""
        try:
            start_time = asyncio.get_event_loop().time()
            if message["type"] != "message":
                return

            data = json.loads(message["data"])
            camera_id = data.get("camera_id")
            logger.info(f"Processing message for camera {camera_id} on channel {channel_name}")

            frame_info = await get_latest_camera_frame(camera_id)
            if frame_info:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"📸 Frame received — Camera {camera_id} @ {frame_info['timestamp']} on channel {channel_name}"
                    )
                )
                # Offload frame processing to Celery
                process_frame_task(frame_info['frame'], channel_name, camera_id, frame_info['timestamp'])
                logger.info(
                    f"Frame dispatched to Celery for camera {camera_id} on channel {channel_name}, "
                    f"processing time: {asyncio.get_event_loop().time() - start_time:.2f}s"
                )
            else:
                self.stderr.write(
                    self.style.WARNING(f"⚠️ No frame found for Camera {camera_id} on channel {channel_name}.")
                )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error processing frame on channel {channel_name}: {e}"))
            logger.error(f"Error processing message for camera {camera_id} on channel {channel_name}: {e}")

    async def listen_to_channel(self, channel_name):
        """Listen to a single Redis Pub/Sub channel."""
        while True:  # Keep trying to reconnect on failure
            try:
                pubsub = camera_redis.pubsub()
                await pubsub.subscribe(channel_name)
                self.stdout.write(
                    self.style.SUCCESS(f"🔌 Subscribed to {channel_name} channel.")
                )

                async for message in pubsub.listen():
                    # Spawn a new task for each message to process in parallel
                    asyncio.create_task(self.process_message(message, channel_name))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Pub/Sub error on channel {channel_name}: {e}"))
                logger.error(f"Pub/Sub error on channel {channel_name}: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def handle_async(self):
        """Async handler for multiple Redis Pub/Sub channels."""
        try:
            # Create tasks for each channel to listen concurrently
            tasks = [self.listen_to_channel(channel) for channel in CHANNEL_NAMES]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ General error in handle_async: {e}"))
            logger.error(f"General error in handle_async: {e}")
            await asyncio.sleep(5)  # Wait before retrying
            await self.handle_async()  # Reconnect on failure

    def handle(self, *args, **kwargs):
        """Entry point for the command."""
        if not CHANNEL_NAMES:
            self.stderr.write(self.style.ERROR("❌ No channels specified in CHANNEL_NAMES."))
            return
        asyncio.run(self.handle_async())


# channel_name = os.getenv("CHANNEL_NAME", "274f0909-1551-4c8e-b1cb-c08166202b08")

# class Command(BaseCommand):
#     help = "Listen for camera frame events via Redis Pub/Sub asynchronously"

#     async def process_message(self, message):
#         """Process a single Pub/Sub message in a separate task."""
#         try:
#             start_time = asyncio.get_event_loop().time()
#             if message["type"] != "message":
#                 return

#             data = json.loads(message["data"])
#             camera_id = data.get("camera_id")
#             logger.info(f"Processing message for camera {camera_id}")

#             frame_info = await get_latest_camera_frame(camera_id)
#             if frame_info:
#                 self.stdout.write(
#                     self.style.SUCCESS(
#                         f"📸 Frame received — Camera {camera_id} @ {frame_info['timestamp']}"
#                     )
#                 )
#                 # Offload frame processing to Celery
#                 process_frame_task.delay(frame_info['frame'], channel_name, camera_id, frame_info['timestamp'])
#                 logger.info(
#                     f"Frame dispatched to Celery for camera {camera_id}, "
#                     f"processing time: {asyncio.get_event_loop().time() - start_time:.2f}s"
#                 )
#             else:
#                 self.stderr.write(
#                     self.style.WARNING(f"⚠️ No frame found for Camera {camera_id}.")
#                 )
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f"❌ Error processing frame: {e}"))
#             logger.error(f"Error processing message for camera {camera_id}: {e}")

#     async def handle_async(self):
#         """Async handler for Redis Pub/Sub."""
#         try:
#             pubsub = camera_redis.pubsub()
#             await pubsub.subscribe(channel_name)
#             self.stdout.write(
#                 self.style.SUCCESS(f"🔌 Subscribed to {channel_name} channel.")
#             )

#             async for message in pubsub.listen():
#                 # Spawn a new task for each message to process in parallel
#                 asyncio.create_task(self.process_message(message))
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f"❌ Pub/Sub error: {e}"))
#             logger.error(f"Pub/Sub error: {e}")
#             await asyncio.sleep(5)  # Wait before retrying
#             await self.handle_async()  # Reconnect on failure

#     def handle(self, *args, **kwargs):
#         """Entry point for the command."""
#         asyncio.run(self.handle_async())

