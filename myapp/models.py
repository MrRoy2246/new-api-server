from django.db import models
from django.db.models import JSONField 
import shortuuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
logger = logging.getLogger(__name__)
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
    ml_attributes = JSONField(null=True, blank=True)
    objects = VisitorManager()
    all_objects = models.Manager()
    def __str__(self):
        return f"{self.first_name} and id {self.id}"
    def soft_delete(self):
        self.is_deleted = True
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


@receiver(post_save, sender=VisitorEventHistory)
def send_event_to_ws(sender, instance, created, **kwargs):
    if not created:
        return
    logger.info("🔔 VisitorEventHistory created, preparing WebSocket message...")
    try: 
        if not instance.camera_id:
            logger.warning("Missing camera_id in VisitorEventHistory instance; deleting event.")
            instance.delete()
            return send_ws_error("Camera ID missing from VisitorEventHistory instance", "unknown")
        
        camera = Camera.objects.get(camera_id=instance.camera_id)
        if not camera:
            logger.warning(f"Camera with ID {instance.camera_id} not found; deleting event.")
            instance.delete()
            return send_ws_error("Camera not found in local database", instance.camera_id)
        
        
        visitors = Visitor.objects.filter(id__in=instance.visitor_ids)

        instance.camera_location = camera.location_name
        instance.latitude = camera.latitude
        instance.longitude = camera.longitude
        instance.institute = camera.institute
        instance.camera_model = camera.camera_model
        instance.video_process_server_id = (camera.video_process_server_info or {}).get("video_process_server_id")
        instance.video_process_server_fixed_id = (camera.video_process_server_info or {}).get("video_process_server_fixed_id")
        instance.video_process_server_ip = (camera.video_process_server_info or {}).get("ip_address")
        instance.visitor_ids = [str(visitor.id) for visitor in visitors]
        instance.save(update_fields=[
            "camera_location", "latitude", "longitude", "snapshot_url",
            "institute", "camera_model", "video_process_server_id",
            "video_process_server_fixed_id", "video_process_server_ip",
            "visitor_ids"
        ])

        visitors_info = []
        for visitor in visitors:
            visitors_info.append({
            "id": visitor.id,
            "first_name": visitor.first_name,
            "last_name": visitor.last_name,
            "email": visitor.email,
            "phone_number": visitor.phone_number,
            "visitor_type": visitor.visitor_type,
            "gender": visitor.gender,
            # "photo": visitor.photo.url if visitor.photo else None,
            "track_status": visitor.track_status
    })

        # create websocket message
        message = {
            "event": "visitor_detected",
            "camera_id": instance.camera_id,
            "location": instance.camera_location,
            "latitude": instance.latitude,
            "longitude": instance.longitude,
            "visitor_ids": instance.visitor_ids,
            "detected_time": instance.detected_time.isoformat(),
            "capture_time": instance.capture_time,
            "snapshot_url": instance.snapshot_url,
            "camera_model": camera.camera_model,
            "camera_type": camera.camera_type,
            "camera_manufacture": camera.camera_manufacture,
            "video_process_server_info": camera.video_process_server_info,
            "third_party_info": camera.third_party_info,
            "visitors": visitors_info
        }
        group_name = "visitor_events"
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification_message",
                "message": message,
            }
        )
        logger.info(f"✅ WebSocket event sent for camera {instance.camera_id}")
    except Exception as e:
        logger.error(f"❌ send_event_to_ws failed: {e}")


def send_ws_error(error_message, camera_id):
    """Send error message via WebSocket"""
    message = {
        "event": "error",
        "camera_id": str(camera_id),
        "error": error_message,
    }
    try:
        group_name = "visitor_events"
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification.message",
                "message": message,
            }
        )
        logger.warning(f"⚠️ Sent WebSocket error message for camera {camera_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send WebSocket error message: {e}")

