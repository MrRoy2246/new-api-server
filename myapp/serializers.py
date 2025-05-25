from rest_framework import serializers
from .models import Visitor
from .ml_models.face_detector import face_detector_instance
from PIL import Image
import cv2
import numpy as np
class VisitorSerializer(serializers.ModelSerializer):
    face_detect = serializers.BooleanField(write_only=True, required=False, default=True)
    # visitor_type_display = serializers.SerializerMethodField()
    visitor_type = serializers.ChoiceField(
        choices=Visitor.VISITOR_TYPE_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True,
        error_messages={
            'invalid_choice': 'Invalid visitor type. Must be one of: employe, contractor, guest, or vendor.'
        }
    )
    class Meta:
        model = Visitor
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'company_name',
            'gender',
            'visitor_type', 
            'identification_type',
            'identification_number',
            'photo',
            'entry_time',
            'exit_time',
            'note',
            'track_status',
            'is_tracking_enabled',
            'created_at',
            'updated_at',
            'face_detect',
            'ml_attributes',  # ✅ ADD THIS
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    def create(self, validated_data):
        validated_data.pop('face_detect', None)  # Remove before saving
        return super().create(validated_data)

    def validate_email(self, value):
        # Exclude self when updating
        instance = self.instance
        if Visitor.all_objects.filter(email=value).exclude(pk=getattr(instance, 'pk', None)).exists():
            raise serializers.ValidationError("A visitor with this email already exists.")
        return value
    def validate_phone_number(self, value):
        # Exclude self when updating
        instance = self.instance
        if Visitor.all_objects.filter(phone_number=value).exclude(pk=getattr(instance, 'pk', None)).exists():
            raise serializers.ValidationError("A visitor with this phone number already exists.")
        return value

    def validate_photo(self, image):
        if not image:
            raise serializers.ValidationError("Photo is required.")
        
        # Check if face detection is required
        face_detect = self.initial_data.get('face_detect', True)
        if not face_detect or str(face_detect).lower() == "false":
            image.seek(0)  # Reset pointer for saving
            return image  # Skip all validations
        try:
            img_pil = Image.open(image)
            image_format = img_pil.format.lower()
            if image_format not in ['jpeg', 'png']:
                raise serializers.ValidationError("Unsupported image format. Only JPEG and PNG are allowed.")
        except Exception:
            raise serializers.ValidationError("Invalid image or unreadable format.")
        # Check file size (<5MB)
        max_size = 5 * 1024 * 1024
        if image.size > max_size:
            raise serializers.ValidationError("Image size must be under 5MB.")
        #Decode image for OpenCV processing
        image.seek(0)  # Important: reset pointer for reading raw bytes
        file_bytes = np.asarray(bytearray(image.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            raise serializers.ValidationError("Failed to decode image.")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Blur check
        if cv2.Laplacian(gray, cv2.CV_64F).var() < 100.0:
            raise serializers.ValidationError("Image is too blurry. Please upload a clearer photo.")
        # Detect face
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = face_detector_instance.detect(img_rgb)
        if not results.detections:
            raise serializers.ValidationError("No face detected.")
        if len(results.detections) > 1:
            raise serializers.ValidationError("Multiple faces detected. Upload a photo with only one face.")
        #Check frontal face 
        detection = results.detections[0]
        keypoints = detection.location_data.relative_keypoints
        left_eye = keypoints[0]
        right_eye = keypoints[1]
        nose_tip = keypoints[2]
        mouth = keypoints[3] 
        # Reject side-views (yaw)
        eye_center_x = (left_eye.x + right_eye.x) / 2.0
        nose_center_offset = abs(nose_tip.x - eye_center_x)
        # print(f"this is nose center offset{nose_center_offset}")
        if nose_center_offset > 0.02:
            raise serializers.ValidationError("Face is turned sideways. Please face the camera.")
        # Reject looking up/down (pitch)
        eye_center_y = (left_eye.y + right_eye.y) / 2.0
        # Distances
        eye_to_nose = nose_tip.y - eye_center_y
        nose_to_mouth = mouth.y - nose_tip.y
        # Ratio check for up/down pose
        ratio = eye_to_nose / (nose_to_mouth + 1e-6)  # avoid zero division
        # print(f"ratio is {ratio}")
        if ratio < 0.75:
            raise serializers.ValidationError("Looking up. Please face the camera.")
        elif ratio > 1.9:
            raise serializers.ValidationError("Looking down. Please face the camera.")
        image.seek(0)  # Reset pointer again for Django saving
        return image







class VisitorWithTypeSerializer(serializers.ModelSerializer):
    visitor_type = serializers.SerializerMethodField()
    class Meta:
        model = Visitor
        fields = ['id', 'first_name', 'last_name','email', 'visitor_type']
    def get_visitor_type(self, obj):
        return {
            "type": obj.get_visitor_type_display()
        }
    





    # for report serializer when many to many------->



# from rest_framework import serializers
# from .models import Visitor, VisitorEventHistory

# class VisitorBasicSerializer(serializers.ModelSerializer):
#     name = serializers.SerializerMethodField()
#     visitor_id = serializers.SerializerMethodField()

#     class Meta:
#         model = Visitor
#         fields = ['visitor_id', 'name', 'email', 'visitor_type', 'company_name']

#     def get_name(self, obj):
#         return f"{obj.first_name} {obj.last_name}"
#     def get_visitor_id(self, obj):
#         return str(obj.id)  # return UUID as string if necessary


# # class VisitorEventHistorySerializer(serializers.ModelSerializer):
# #     visitors = VisitorBasicSerializer(many=True)
# #     # camera = serializers.SerializerMethodField()
# #     detect_id = serializers.SerializerMethodField()

# #     class Meta:
# #         model = VisitorEventHistory
# #         fields = [
# #             'detect_id', 'camera_id','camera_location','latitude', 'longitude', 'snapshot_url', 'capture_time', 'detected_time', 
# #             'visitors', 
# #         ]

# #     def get_detect_id(self, obj):
# #         return f"detect-{obj.id}"
    
# class VisitorEventHistorySerializer(serializers.ModelSerializer):
#     visitors = serializers.SerializerMethodField()  # ✅ fixed
#     detect_id = serializers.SerializerMethodField()

#     class Meta:
#         model = VisitorEventHistory
#         fields = [
#             'detect_id', 'camera_id', 'camera_location', 'latitude', 'longitude',
#             'snapshot_url', 'capture_time', 'detected_time', 'visitors',
#         ]

#     def get_detect_id(self, obj):
#         return f"detect-{obj.id}"

#     def get_visitors(self, obj):
#         visitors = Visitor.objects.filter(id__in=obj.visitor_ids)
#         return VisitorBasicSerializer(visitors, many=True).data






# without many to many----->
    
# serializers.py
from rest_framework import serializers
from .models import VisitorEventHistory, Visitor

class VisitorBasicSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    visitor_id = serializers.SerializerMethodField()

    class Meta:
        model = Visitor
        fields = ['visitor_id', 'name', 'email', 'visitor_type', 'company_name']

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_visitor_id(self, obj):
        return str(obj.id)


class VisitorEventHistorySerializer(serializers.ModelSerializer):
    visitors = serializers.SerializerMethodField()
    detect_id = serializers.SerializerMethodField()

    class Meta:
        model = VisitorEventHistory
        fields = [
            'detect_id', 'camera_id', 'camera_location', 'latitude', 'longitude',
            'snapshot_url', 'capture_time', 'detected_time', 'visitors',
        ]

    def get_detect_id(self, obj):
        return f"detect-{obj.id}"

    def get_visitors(self, obj):
        visitors = Visitor.objects.filter(id__in=obj.visitor_ids)
        return VisitorBasicSerializer(visitors, many=True).data
