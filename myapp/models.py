
from django.db import models
from django.db.models import JSONField 
import uuid
import shortuuid
import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import timezone 
from datetime import datetime, timedelta
import logging
def generate_short_id():
    return shortuuid.ShortUUID().random(length=8)
class VisitorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
class Visitor(models.Model):
    IDENTIFICATION_CHOICES = [
        ('nid', 'NID'),
        ('passport', 'Passport'),
        ('driving', 'Driving License'),
    ]
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    VISITOR_TYPE_CHOICES = [
        ('employe', 'Employee'),
        ('contractor', 'Contractor'),
        ('guest', 'Guest'),
        ('vendor', 'Vendor'),
    ]
    id = models.CharField(primary_key=True, default=generate_short_id, editable=False, max_length=8, unique=True)
    first_name = models.CharField(max_length=50) #required
    last_name = models.CharField(max_length=50) #required
    email = models.EmailField() #required
    phone_number = models.CharField(max_length=20) #required
    company_name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='other') #required
    visitor_type = models.CharField(max_length=20 ,choices=VISITOR_TYPE_CHOICES, default='guest',blank=True,null=True)
    identification_type = models.CharField(max_length=10, choices=IDENTIFICATION_CHOICES,null=True, blank=True)
    identification_number = models.CharField(max_length=50,null=True, blank=True)
    photo = models.ImageField(
        upload_to='localtest/visitor_photos/', 
        null=True, 
        blank=True
    ) #required
    entry_time = models.DateTimeField(null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    track_status = models.BooleanField(default=False) 
    is_deleted = models.BooleanField(default=False)
    is_tracking_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True) 
    # ml attribute to store mlserver response in our databse------------
    ml_attributes = JSONField(null=True, blank=True)
    objects = VisitorManager()
    all_objects = models.Manager()
    def __str__(self):
        return f"{self.first_name} and id {self.id}"
    def soft_delete(self):
        self.is_deleted = True
        # self.track_status = False
        self.save()
    def restore(self):
        self.is_deleted = False
        self.save()
class VisitorEventHistory(models.Model):
    camera_id = models.CharField(max_length=100)
    camera_location = models.CharField(max_length=255,null =True ,blank =True)
    latitude = models.CharField(max_length=100, null=True, blank=True)
    longitude = models.CharField(max_length=100, null=True, blank=True)
    snapshot_url = models.URLField()
    capture_time = models.CharField(max_length=100)  # Adjust length as needed     
    detected_time = models.DateTimeField()
    visitor_ids = JSONField(default=list)
    visitors = models.ManyToManyField(Visitor, related_name='event_histories')
    institute = models.CharField(max_length=255, null=True, blank=True)
    camera_model = models.CharField(max_length=100, null=True, blank=True)
    video_process_server_id = models.CharField(max_length=100, null=True, blank=True)
    video_process_server_fixed_id = models.CharField(max_length=100, null=True, blank=True)
    video_process_server_ip = models.CharField(max_length=100,null=True, blank=True)
    def __str__(self):
        return f"Event at {self.camera_location} on {self.capture_time}"
# camera Model------->
class Camera(models.Model):
    camera_id = models.CharField(max_length=100, unique=True)
    url = models.TextField()
    location_name = models.CharField(max_length=255)
    institute = models.IntegerField()
    latitude = models.CharField(max_length=50)
    longitude = models.CharField(max_length=50)
    camera_running_status = models.BooleanField(default=False)
    camera_frame_cap_status = models.BooleanField(default=False)
    video_process_server = models.IntegerField(null=True, blank=True)
    camera_type = models.CharField(max_length=50)
    camera_model = models.CharField(max_length=255, blank=True)
    camera_manufacture = models.CharField(max_length=255, blank=True)
    threshold = models.CharField(max_length=10)
    third_party = models.IntegerField(null=True, blank=True)
    video_process_server_info = models.JSONField(null=True, blank=True)
    third_party_info = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.camera_id




# @receiver(post_save, sender=VisitorEventHistory)
# def send_event_to_ws(sender, instance, created, **kwargs):
#     if not created:
#         return
#     try:
#         token = get_request_token()  #Fetch token dynamically
#         if not token:
#             logger.warning("⚠️ Token not found on instance")
#             return  # Don't delete the instance unless you're sure
#         camera_id = instance.camera_id
#         # Decode institute_id from JWT token
#         decoded_token = jwt.decode(token, options={"verify_signature": False})
#         institute_id = decoded_token.get("institute")
#         if not institute_id:
#             logger.warning("❌ Token does not contain institute info")
#             instance.delete()
#             return send_ws_error("Invalid token: missing institute info", camera_id)
#         # ✅ Validate camera exists in institute
#         try:
#             valid = is_camera_valid_for_institute(camera_id, institute_id, token)
#             if not valid:
#                 logger.warning(f"❌ Camera {camera_id} not found in institute {institute_id}")
#                 instance.delete()
#                 return send_ws_error("Camera does not exist in your institute", camera_id)
#         except PermissionError as e:
#             logger.warning(f"🔐 Token issue while validating camera list: {e}")
#             instance.delete()
#             return send_ws_error("Token is invalid or expired", camera_id)
#         # ✅ Fetch full camera info
#         camera_info = get_camera_info(camera_id, token)
#         if not camera_info:
#             logger.warning(f"🚫 Could not fetch camera info for camera_id: {camera_id}")
#             instance.delete()
#             return send_ws_error("Unable to fetch camera metadata", camera_id)
#         # ➕ Update instance
#         instance.camera_location = camera_info.get("location_name")
#         instance.latitude = camera_info.get("latitude")
#         instance.longitude = camera_info.get("longitude")
#         instance.snapshot_url = camera_info.get("snapshot_url", "https://default.snapshot")
#         instance.institute = camera_info.get("institute")
#         instance.camera_model = camera_info.get("camera_model")
#         instance.video_process_server_id = camera_info.get("video_process_server_id")
#         instance.video_process_server_fixed_id = camera_info.get("video_process_server_fixed_id")
#         instance.video_process_server_ip = camera_info.get("video_process_server_ip")
#         instance.save(update_fields=[
#             "camera_location", "latitude", "longitude", "snapshot_url",
#             "institute", "camera_model", "video_process_server_id",
#             "video_process_server_fixed_id", "video_process_server_ip"
#         ])
#         instance.visitor_ids = [str(visitor.id) for visitor in instance.visitors.all()]
#         instance.save(update_fields=["visitor_ids"])
#         # 📡 Send success WebSocket message
#         message = {
#             "event": "visitor_detected",
#             "camera_id": camera_id,
#             "location": instance.camera_location,
#             "latitude": instance.latitude,
#             "longitude": instance.longitude,
#             # "visitor_ids": [str(uid) for uid in instance.visitor_ids],
#             "visitor_ids": [str(visitor_id) for visitor_id in instance.visitor_ids],  # ✅ Updated here
#             # "visitor_ids": [visitor.id for visitor in instance.visitors.all()],
#             "detected_time": instance.detected_time.isoformat(),
#             "capture_time": instance.capture_time.isoformat(),
#             "snapshot_url": instance.snapshot_url,
#         }
#         group_name = "visitor_events"
#         channel_layer = get_channel_layer()
#         async_to_sync(channel_layer.group_send)(
#             group_name,
#             {
#                 "type": "notification.message",
#                 "message": message,
#             }
#         )
#         logger.info(f"✅ WebSocket event sent for camera {camera_id}")
#     except Exception as e:
#         logger.error(f"❌ send_event_to_ws failed: {e}")



# # -----
    

# logger = logging.getLogger(__name__)
# @receiver(post_save, sender=VisitorEventHistory)
# def send_event_to_ws(sender, instance, created, **kwargs):
#     if not created:
#         return
#     try:
#         print("this is receiver model running")
        
#         if not instance.camera_id:
#             instance.delete()
#             return send_ws_error("Camera ID missing from VisitorEventHistory instance", "unknown")

#         try:
#             camera = Camera.objects.get(camera_id=instance.camera_id)
#         except Camera.DoesNotExist:
#             instance.delete()
#             return send_ws_error("Camera not found in local database", instance.camera_id)
        
#         instance.camera_location = camera.location_name
#         instance.latitude = camera.latitude
#         instance.longitude = camera.longitude
#         instance.institute = camera.institute
#         instance.camera_model = camera.camera_model
#         instance.video_process_server_id = (camera.video_process_server_info or {}).get("video_process_server_id")
#         instance.video_process_server_fixed_id = (camera.video_process_server_info or {}).get("video_process_server_fixed_id")
#         instance.video_process_server_ip = (camera.video_process_server_info or {}).get("ip_address")
#         instance.visitor_ids = [str(visitor.id) for visitor in instance.visitors.all()]
#         instance.save(update_fields=[
#             "camera_location", "latitude", "longitude", "snapshot_url",
#             "institute", "camera_model", "video_process_server_id",
#             "video_process_server_fixed_id", "video_process_server_ip",
#             "visitor_ids"
#         ])
#         photo_urls = [v.photo.url for v in instance.visitors.all() if v.photo]
#         message = {
#             "event": "visitor_detected",
#             "camera_id": instance.camera_id,
#             "location": instance.camera_location,
#             "latitude": instance.latitude,
#             "longitude": instance.longitude,
#             "visitor_ids": instance.visitor_ids,
#             "detected_time": instance.detected_time.isoformat(),
#             "capture_time": instance.capture_time, # It's now a string
#             "snapshot_url": photo_urls,
#         }
#         group_name = "visitor_events"
#         channel_layer = get_channel_layer()
#         async_to_sync(channel_layer.group_send)(
#             group_name,
#             {
#                 "type": "notification.message",
#                 "message": message,
#             }
#         )
#         logger.info(f"✅ WebSocket event sent for camera {instance.camera_id}")
#     except Exception as e:
#         logger.error(f"❌ send_event_to_ws failed: {e}")

# def send_ws_error(error_message, camera_id):
#     """Send error message via WebSocket"""
#     message = {
#         "event": "error",
#         "camera_id": str(camera_id),
#         "error": error_message,
#     }
#     group_name = "visitor_events"
#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         group_name,
#         {
#             "type": "notification.message",
#             "message": message,
#         }
#     )








logger = logging.getLogger(__name__)
import jwt
import requests
from myapp.utils import get_request_token
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
@receiver(m2m_changed, sender=VisitorEventHistory.visitors.through)
def visitors_m2m_changed(sender, instance, action, **kwargs):
    print("🚨 visitors_m2m_changed triggered with action:", action)
    if action != 'post_add':
        return
    try:
        print("this is receiver model running")
        
        if not instance.camera_id:
            instance.delete()
            return send_ws_error("Camera ID missing from VisitorEventHistory instance", "unknown")

        try:
            camera = Camera.objects.get(camera_id=instance.camera_id)
        except Camera.DoesNotExist:
            instance.delete()
            return send_ws_error("Camera not found in local database", instance.camera_id)
        instance.camera_location = camera.location_name
        instance.latitude = camera.latitude
        instance.longitude = camera.longitude
        instance.institute = camera.institute
        instance.camera_model = camera.camera_model
        instance.video_process_server_id = (camera.video_process_server_info or {}).get("video_process_server_id")
        instance.video_process_server_fixed_id = (camera.video_process_server_info or {}).get("video_process_server_fixed_id")
        instance.video_process_server_ip = (camera.video_process_server_info or {}).get("ip_address")
        instance.visitor_ids = [str(visitor.id) for visitor in instance.visitors.all()]
        instance.save(update_fields=[
            "camera_location", "latitude", "longitude", "snapshot_url",
            "institute", "camera_model", "video_process_server_id",
            "video_process_server_fixed_id", "video_process_server_ip",
            "visitor_ids"
        ])
        photo_urls = [v.photo.url for v in instance.visitors.all() if v.photo]
        # message = {
        #     "event": "visitor_detected",
        #     "camera_id": instance.camera_id,
        #     "location": instance.camera_location,
        #     "latitude": instance.latitude,
        #     "longitude": instance.longitude,
        #     "visitor_ids": instance.visitor_ids,
        #     "detected_time": instance.detected_time.isoformat(),
        #     "capture_time": instance.capture_time, # It's now a string
        #     "snapshot_url": photo_urls,
        # }
        data={'event': 'visitor_detected', 
              'camera_id': '124', 
              'location': 'Camera', 
              'latitude': '0.000000', 
              'longitude': '0.000000', 
              'visitor_ids': ['7uNR8KL3', 'gPAEAveY'],
            'detected_time': '2025-05-13T11:32:55.805407+00:00', 
            'capture_time': '2025-05-11 11:52', 
            'snapshot_url': ['http://192.168.1.150:9000/abin-roy/localtest/visitor_photos/visitor_female.jpg', 'http://192.168.1.150:9000/abin-roy/localtest/visitor_photos/visitor%20imagejpg.jpg']}
        group_name = "visitor"
        channel_layer = get_channel_layer()
        print("abin")
        print(f"this is test message{data}")
        print(type(data))
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification.message",
                "message": data,
            }
        )
        logger.info(f"✅ WebSocket event sent for camera {instance.camera_id}")
        print("roy")
    except Exception as e:
        logger.error(f"❌ visitors_m2m_changed failed: {e}")


def send_ws_error(error_message, camera_id):
    """Send error message via WebSocket"""
    message = {
        "event": "error",
        "camera_id": str(camera_id),
        "error": error_message,
    }
    group_name = "visitor_events"
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "notification.message",
            "message": message,
        }
    )




# def decode_token_institute(token):
#     try:
#         decoded = jwt.decode(token, options={"verify_signature": False})
#         return decoded.get("institute")
#     except Exception as e:
#         logger.error(f"Token decode error: {e}")
#         return None
# # Validate if camera exists for institute
# def is_camera_valid_for_institute(camera_id, institute_id, token):
#     try:
#         url = f"https://api.accelx.net/gd_apidev/camera/camera-setups/?institute={institute_id}"
#         headers = {
#             'Authorization': f'Bearer {token}',
#             'Content-Type': 'application/json'
#         }
#         response = requests.get(url, headers=headers)
#         if response.status_code == 200:
#             camera_list = response.json()
#             return any(str(cam.get("id")) == str(camera_id) for cam in camera_list)
#         elif response.status_code in (401, 403):
#             logger.error(f"🔒 Token error: {response.status_code}")
#             raise PermissionError("Token is invalid or expired")
#         logger.error(f"⚠️ Unexpected error validating camera list: {response.status_code}")
#         return False
#     except PermissionError:
#         raise  # Let caller handle token error specifically
#     except Exception as e:
#         logger.error(f"❌ Exception in camera validation: {e}")
#         return False
# # Get full camera info
# def get_camera_info(camera_id, token):
#     try:
#         url = f"https://api.accelx.net/gd_apidev/camera/camera-setups/{camera_id}/"
#         headers = {
#             'Authorization': f'Bearer {token}',
#             'Content-Type': 'application/json'
#         }
#         response = requests.get(url, headers=headers)
#         if response.status_code == 200:
#             data = response.json()
#             return {
#                 'latitude': data.get('latitude'),
#                 'longitude': data.get('longitude'),
#                 'location_name': data.get('location_name'),
#                 # 'snapshot_url': data.get('url'),
#                 'institute': data.get('institute'),
#                 'camera_model': data.get('camera_model'),
#                 'video_process_server_id': data.get('video_process_server_info', {}).get('video_process_server_id'),
#                 'video_process_server_fixed_id': data.get('video_process_server_info', {}).get('video_process_server_fixed_id'),
#                 'video_process_server_ip': data.get('video_process_server_info', {}).get('ip_address'),
#             }
#         logger.error(f"Camera API response error: {response.status_code}")
#         return None
#     except Exception as e:
#         logger.error(f"Camera API call failed: {e}")
#         return None
