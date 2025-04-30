import json
from channels.generic.websocket import AsyncWebsocketConsumer
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import authenticate
from django.core.files.uploadedfile import SimpleUploadedFile
from channels.exceptions import StopConsumer
import logging
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=3)
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.group_name = self.scope['url_route']['kwargs']['group_name']
            # self.camera_id = self.scope['url_route']['kwargs']['camera_id']
            # self.group_name = f"visitor_events_camera_{self.camera_id}"
        except KeyError:
            await self.send_error_message("Group name is missing.")
            return
        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"WebSocket connected to group: {self.group_name}") 
        except Exception as e:
            await self.send_error_message("Group name is missing.")
    async def receive(self, text_data):
        """Handle messages received from the WebSocket client."""
        try:
            data = json.loads(text_data)
            message = data.get('message', 'No message received')
            logger.info(f"🔹 Received from client: {message}")
            print(f"🔹 Received from client: {message}")  # Fallback to print
            await self.send(text_data=json.dumps({
                'message': f"You said: {message}"
            }))
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'notification.message',
                    'message': f"{message} (broadcasted)"
                }
            )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected from group: {self.group_name}")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    async def notification_message(self, event):
        message = event['message']
        print("Message backend :", message)  
        await self.send(text_data=json.dumps({
            'message': message,
        }))
    async def send_error_message(self, error_message):
        """ Helper function to send an error message to the WebSocket """
        await self.send(text_data=json.dumps({
            'error': error_message
        }))
        await self.close()
    async def close(self):
        """ Custom close logic """
        await self.send(text_data=json.dumps({
            'error': 'Invalid connection attempt or group name missing.'
        }))
        raise StopConsumer()  # Gracefully stop the consumer
