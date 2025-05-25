from django.shortcuts import render
import requests
import jwt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Visitor,VisitorEventHistory,Camera
from .serializers import VisitorSerializer
from rest_framework.pagination import PageNumberPagination
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from dateutil.parser import parse as parse_datetime
from .utils import get_minio_client
from django.conf import settings
import difflib
from rest_framework.exceptions import ValidationError

class VisitorPagination(PageNumberPagination):
    page_size = 10 
class VisitorBaseView(APIView):
    def get_token_from_header(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token ') or auth_header.startswith('Bearer '):
            parts = auth_header.split(' ')
            if len(parts) == 2:
                return parts[1]
        return None
    def is_token_valid(self, token):
        url = "https://api.accelx.net/gd_apidev/user/token/verify/"
        try:
            response = requests.post(url, json={"token": token})
            return response.status_code == 200
        except requests.RequestException:
            return False
    def get_role_from_token(self, token):
        try:
            decoded = jwt.decode(token,options={"verify_signature": False})
            return decoded.get("role")
        except jwt.DecodeError:
            return None
    def get_institute_from_token(self, token):
        try:
            decoded = jwt.decode(token,options={"verify_signature": False})
            return decoded.get("institute")
        except jwt.DecodeError:
            return None
class VisitorAPIView(VisitorBaseView):
    pagination_class = VisitorPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    def get_queryset(self, request):
        only_deleted = request.query_params.get('only_deleted')
        visitor_type_param = request.query_params.get('visitor_type')
        track_status = request.query_params.get('track_status')
        queryset = Visitor.all_objects.all()  # Start with all visitors
        if only_deleted == 'true':
            queryset = queryset.filter(is_deleted=True)
        elif only_deleted == 'false':
            queryset = queryset.filter(is_deleted=False)
        if visitor_type_param:
            visitor_types = [vt.strip().lower() for vt in visitor_type_param.split(',')]
            valid_types = [choice[0] for choice in Visitor.VISITOR_TYPE_CHOICES]
            invalid_types = [t for t in visitor_types if t not in valid_types]
            if invalid_types:
                suggestions = {
                    t: difflib.get_close_matches(t, valid_types, n=1)
                    for t in invalid_types
                }
                raise ValidationError({
                    "error": "Invalid visitor_type value(s).",
                    "invalid": invalid_types,
                    "did_you_mean": {k: v[0] if v else None for k, v in suggestions.items()}
                })
            queryset = queryset.filter(visitor_type__in=visitor_types)
        if track_status is not None:
            if track_status.lower() == 'true':
                queryset = queryset.filter(track_status=True)
            elif track_status.lower() == 'false':
                queryset = queryset.filter(track_status=False)
        return queryset.order_by('-created_at')
    def get(self, request, pk=None):
        if pk:
            try:
                visitor = Visitor.all_objects.get(pk=pk)
            except Visitor.DoesNotExist:
                return Response({'error': 'Visitor not found'}, status=404)
            serializer = VisitorSerializer(visitor)
            return Response(serializer.data)
        queryset = self.get_queryset(request)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = VisitorSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    def post(self, request):
        photo = request.FILES.get('photo')
        visitor_fields = {
            "first_name": request.data.get('first_name'),
            "last_name": request.data.get('last_name'),
            "email": request.data.get('email'),
            "phone_number": request.data.get('phone_number'),
            "gender": request.data.get('gender'),
            "photo": photo,
            'face_detect': request.data.get('face_detect', True),
        }
        required_fields = ['first_name', 'last_name', 'email', 'phone_number', 'gender']
        missing = [field for field in required_fields if not visitor_fields.get(field)]
        if missing:
            return Response({"error": f"Missing required fields: {', '.join(missing)}"}, status=400)
        serializer = VisitorSerializer(data=visitor_fields)
        if serializer.is_valid():
            file_key = None
            if not photo:
                return Response({"error": "Photo is required."}, status=400)
            s3 = get_minio_client()
            file_key = f"localtest/visitor_photos/{photo.name}"
            try:
                s3.upload_fileobj(
                    photo,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    file_key,
                    ExtraArgs={'ContentType': photo.content_type}
                )
            except Exception as e:
                return Response({"error": f"Image upload failed: {str(e)}"}, status=500)
            serializer.validated_data.pop('photo', None)
            try:
                visitor = serializer.save()
            except Exception as e:
                return Response({"error": f"Database save failed: {str(e)}"}, status=500)
            if file_key:
                visitor.photo.name = file_key
                visitor.save()
            # send ml server to store the ml response-------------
            ml_response= self.send_to_ml_server(visitor)
            print(f"this is ml server response={ml_response}")
            if isinstance(ml_response, dict) and 'ml_attributes' in ml_response:
                attribute_values = list(ml_response['ml_attributes'].values())
                visitor.ml_attributes = attribute_values
                visitor.save()
                print("Stored ml_attributes in DB:", visitor.ml_attributes)
            return Response(VisitorSerializer(visitor).data, status=201)
        return Response(serializer.errors, status=400)
    def send_to_ml_server(self,visitor):
        photo_url= visitor.photo.url
        photo_data= requests.get(photo_url).content
        try:
            response= requests.post("http://localhost:8000/api/mock-ml/",
                                    # files={'frame':photo_data},
                                    files={'frame': ('photo.jpg', photo_data, 'image/jpeg')},
                                    # data={'visitor_id':visitor.id}
                                    )
            if response.status_code==200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"Error Sending to Ml server: {e}")
            return None


    def put(self, request, pk):
        try:
            visitor = Visitor.all_objects.get(pk=pk)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=404)
        serializer = VisitorSerializer(visitor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    def delete(self, request, pk):
        try:
            visitor = Visitor.all_objects.get(pk=pk)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=404)
        permanent = request.query_params.get('permanent') == 'true'
        if permanent:
            try:
                visitor.delete()
                return Response({'message': 'Visitor permanently deleted'}, status=200)
            except Exception as e:
                return Response({'error': f'Permanent delete failed: {str(e)}'}, status=500)  
        if visitor.is_deleted:
            return Response({'error': 'Visitor is already soft-deleted.'}, status=409)
        visitor.soft_delete()
        return Response({'message': 'Visitor soft deleteded successfully.'}, status=200)
class RestoreVisitorAPIView(VisitorBaseView):
    def post(self, request, pk):
        try:
            visitor = Visitor.all_objects.get(pk=pk, is_deleted=True)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found or not deleted'}, status=404)
        visitor.restore()
        return Response({'message': 'Visitor restored successfully'}, status=200)
    

import random
class MockMLServerView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    ATTRIBUTE_LIST =  [
        'A pedestrian wearing a hat',
        'A pedestrian wearing sunglasses',
        'A pedestrian with long hair',
        'A pedestrian in a jacket',
        'A pedestrian in jeans',
        'A pedestrian in sneakers',
        'A pedestrian with a backpack',
        'A pedestrian under the age of 30',
        'A pedestrian over the age of 60',
        'A male pedestrian',
    ]

    def post(self, request):
        photo = request.FILES.get('frame')
        if not photo:
            return Response({'error': 'No image provided'}, status=400)

        # Generate binary values for each attribute
        attribute_result = {attr: random.randint(0, 1) for attr in self.ATTRIBUTE_LIST}

        return Response({
            "ml_attributes": attribute_result
        }, status=200)



class ToggleTrackingAPIView(VisitorBaseView):
    def post(self, request, pk):
        try:
            visitor = Visitor.all_objects.get(pk=pk)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=404)

        new_status = request.data.get("is_tracking_enabled")
        if new_status is None:
            return Response({'error': 'Missing is_tracking_enabled field in request body.'}, status=400)

        if not isinstance(new_status, bool):
            return Response({'error': 'is_tracking_enabled must be a boolean.'}, status=400)

        visitor.is_tracking_enabled = new_status
        visitor.save()
        return Response({
            'message': f"Tracking status set to {new_status} for visitor {visitor.first_name} and id is {visitor.id}",
            'is_tracking_enabled': visitor.is_tracking_enabled
        }, status=200)


class VisitorLastLocationAPIView(APIView):
    def get(self, request, pk):
        try:
            visitor = Visitor.all_objects.get(pk=pk)
        except Visitor.DoesNotExist:
            return Response({"error": "Visitor not found"}, status=404)

        if not visitor.is_tracking_enabled:
            return Response({"error": "Tracking is disabled for this visitor."}, status=403)

        # Get latest event history involving this visitor
        # latest_event = VisitorEventHistory.objects.filter(
        #     visitor_ids__contains=[visitor.id]
        # ).order_by('-detected_time').first()
        all_events = VisitorEventHistory.objects.order_by('-detected_time')
        latest_event = next(
            (event for event in all_events if str(visitor.id) in event.visitor_ids),
            None
        )

        if not latest_event:
            return Response({"error": "No location history found for this visitor."}, status=404)

        return Response({
            "visitor_id": visitor.id,
            "latitude": latest_event.latitude,
            "longitude": latest_event.longitude,
            "detected_time": latest_event.detected_time.isoformat(),
            "location": latest_event.camera_location
        }, status=200)


# store camera
    
class CameraUpdateView(VisitorBaseView):
    def get(self, request, *args, **kwargs):
        # Make an API call to the external service to get the camera data
        token = self.get_token_from_header(request)
        # print(f"this is token test->{token}")
        if not token or not self.is_token_valid(token):
            return Response({'error': 'Invalid or missing token'}, status=403)
        institute=self.get_institute_from_token(token)
        if not institute:
            return Response({'error': 'No institute in token'}, status=404)
        external_api_url = f"https://api.accelx.net/gd_apidev/camera/camera-setups/?institute={institute}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(external_api_url, headers=headers)
        
        if response.status_code == 200:
            camera_data = response.json()  # Assuming the response is in JSON format
            for data in camera_data:
                # Extract each camera's information from the response
                camera_id = data['id']  # Unique camera identifier
                # Use `update_or_create` to update or create the camera record in your database
                Camera.objects.update_or_create(
                    camera_id=camera_id,  # Use `camera_id` as the unique identifier
                    defaults={  # The `defaults` dictionary will contain all other fields
                        'url': data.get('url', ''),
                        'location_name': data.get('location_name', ''),
                        'institute': data.get('institute', None),
                        'latitude': data.get('latitude', ''),
                        'longitude': data.get('longitude', ''),
                        'camera_running_status': data.get('camera_running_status', False),
                        'camera_frame_cap_status': data.get('camera_frame_cap_status', False),
                        'video_process_server': data.get('video_process_server', None),
                        'camera_type': data.get('camera_type', ''),
                        'camera_model': data.get('camera_model', ''),
                        'camera_manufacture': data.get('camera_manufacture', ''),
                        'threshold': data.get('threshold', ''),
                        'third_party': data.get('third_party', None),
                        'video_process_server_info': data.get('video_process_server_info', {}),
                        'third_party_info': data.get('third_party_info', {}),
                    }
                )
            return Response({"message": "Camera data updated successfully."}, status=200)
        return Response({"message": "Failed to fetch camera data."}, status=400)




# MANUAL TEST-------

import base64
import logging
import requests
from io import BytesIO
from PIL import Image
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from myapp.utils import set_request_token, clear_request_token
from .models import Visitor, VisitorEventHistory
logger = logging.getLogger(__name__)
class MLDetectionAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            frame = request.data.get("frame")
            camera_id = request.data.get("camera_id")
            token = request.headers.get("Authorization")
            if token and token.startswith("Bearer "):
                token = token[len("Bearer "):]
            capture_time = request.data.get("capture_time")
            manual_visitor_ids = request.data.get("visitor_ids")  # Manual test support
            if not (camera_id and token and capture_time):
                return Response({"error": "Missing camera_id, token, or capture_time"}, status=status.HTTP_400_BAD_REQUEST)
            if manual_visitor_ids:
                visitors = Visitor.objects.filter(id__in=manual_visitor_ids)
                if not visitors.exists():
                    return Response({"error": "No valid visitors found"}, status=404)
                try:
                    self.create_event(visitors, camera_id, token, capture_time)
                    return Response({
                        "status": "success",
                        "message": "Manual test: event created",
                        "visitor_ids": manual_visitor_ids
                    }, status=200)
                except Exception as e:
                    return Response({"error": str(e)}, status=400)
            if not frame:
                return Response({"error": "Missing frame for ML processing"}, status=400)
            return Response(self.send_to_ml_server(frame, camera_id, token, capture_time))
        except Exception as e:
            logger.error(f"Error in ML detection view: {e}")
            return Response({"error": "Internal server error"}, status=500)
    def send_to_ml_server(self, frame, camera_id, token, capture_time):
        try:
            frame_data = base64.b64decode(frame)
            img_file = SimpleUploadedFile("frame.jpg", frame_data, content_type="image/jpeg")
            visitor_files = []
            for visitor in Visitor.objects.filter(is_deleted=False, photo__isnull=False):
                try:
                    with visitor.photo.open('rb') as photo_file:
                        visitor_files.append(
                            ('visitor_images', (f"{visitor.id}.jpg", photo_file.read(), 'image/jpeg'))
                        )
                except Exception as e:
                    logger.warning(f"Error reading visitor image: {e}")
            files = [('frame', img_file)] + visitor_files
            response = requests.post("http://mlserver.com/detect", files=files, data={'camera_id': camera_id, 'token': token})
            if response.status_code == 200:
                detection_data = response.json()
                visitor_ids = detection_data.get('visitor_ids', [])
                if visitor_ids:
                    visitors = Visitor.objects.filter(id__in=visitor_ids)
                    self.create_event(visitors, camera_id, token, capture_time)
                    return {"status": "success", "visitor_ids": visitor_ids}
                return {"status": "error", "message": "No visitors detected"}
            return {"status": "error", "message": "ML server error"}
        except Exception as e:
            logger.error(f"ML server communication error: {e}")
            return {"status": "error", "message": "Error contacting ML server"}
    def create_event(self, visitors, camera_id, token, capture_time):
        try:
            set_request_token(token)
            capture_time = capture_time
            detected_time = timezone.now()
            snapshot_url = visitors[0].photo.url if visitors and visitors[0].photo else "https://default.snapshot"
            visitor_ids = [visitor.id for visitor in visitors]
            logger.info(f"➡️ Creating VisitorEventHistory for camera {camera_id}")
            event = VisitorEventHistory.objects.create(
                visitor_ids=visitor_ids,  # Temp empty; will update later
                camera_id=camera_id,
                snapshot_url=snapshot_url,
                capture_time=capture_time,
                detected_time=detected_time,
            )
            # event.visitors.set(visitors)  # This triggers m2m_changed
        except Exception as e:
            logger.error(f"Error creating event or WebSocket send: {e}")
        finally:
            clear_request_token()

class VisitorEventDeleteAPIView(APIView):
    def delete(self, request, pk, *args, **kwargs):
        try:
            event = VisitorEventHistory.objects.get(pk=pk)
            event.delete()
            return Response({"message": "Event deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except VisitorEventHistory.DoesNotExist:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)


# visitor ditection camera detail with token auth    

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import VisitorEventHistory
import base64
import requests
import logging
logger = logging.getLogger(__name__)
def get_base64_from_url(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
        else:
            return None
    except Exception as e:
        return None
class VisitorDetectionsView(APIView):
    def get_token_from_header(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token ') or auth_header.startswith('Bearer '):
            parts = auth_header.split(' ')
            if len(parts) == 2:
                return parts[1]
        return None
    def is_token_valid(self, token):
        url = "https://api.accelx.net/gd_apidev/user/token/verify/"
        try:
            response = requests.post(url, json={"token": token})
            return response.status_code == 200
        except requests.RequestException:
            return False
    def get(self, request, visitor_id):
        try:
            token = self.get_token_from_header(request)
            if not token or not self.is_token_valid(token):
                return Response({'error': 'Invalid or missing token'}, status=403)
            # Manually filter visitor_ids from all objects
            all_detections = VisitorEventHistory.objects.all()
            detections = [d for d in all_detections if visitor_id in d.visitor_ids]
            # detections = VisitorEventHistory.objects.filter(visitors__id=visitor_id)
            detections.sort(key=lambda d: d.id, reverse=True)
            if not detections:
                return Response({"error": "No detections found."}, status=status.HTTP_404_NOT_FOUND)
            data = []
            for d in detections:
                image_base64 = get_base64_from_url(d.snapshot_url)
                # visitor_first_names = [v.first_name for v in d.visitors.all()]    #many to many field er jonno
                visitor_first_names = [v.first_name for v in Visitor.objects.filter(id__in=d.visitor_ids)]
                data.append({
                    "detection_id": f"detect-{d.id}",
                    "cam_id": d.camera_id,
                    "location": d.camera_location,
                    "lat": d.latitude,
                    "long": d.longitude,
                    "detected_time": d.detected_time.isoformat() if d.detected_time else None,
                    "exit_time": None,
                    "image": image_base64,
                    "visitors": visitor_first_names  # 👈 Add first names here
                })
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in VisitorDetectionsView: {e}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -------------------------------work fine only with detecte_time filter--
# report
#     # chat when many to many field was available----->
    
# from django.db.models import Q
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.pagination import PageNumberPagination
# from django.utils import timezone
# from django.db.models import Q, Count
# from django.db.models.functions import TruncHour, TruncDay
# from datetime import timedelta
# from dateutil.parser import parse as parse_datetime
# import logging
# from .models import VisitorEventHistory, Visitor
# from .serializers import VisitorEventHistorySerializer
# logger = logging.getLogger(__name__)
# class VisitorReportPagination(PageNumberPagination):
#     page_size = 10
#     page_size_query_param = 'page_size'
# class VisitorReportAPIView(APIView):
#     pagination_class = VisitorReportPagination
#     def get(self, request):
#         try:
#             start_time = request.query_params.get('start_time')
#             end_time = request.query_params.get('end_time')
#             last_minutes = request.query_params.get('last_minutes')
#             last_days = request.query_params.get('last_days')
#             camera_id = request.query_params.get('camera_id')
#             visitor_id = request.query_params.get('visitor_id')
#             visitor_name = request.query_params.get('visitor_name')
#             # queryset = VisitorEventHistory.objects.prefetch_related('visitors').all().order_by('-detected_time')
#             queryset = VisitorEventHistory.objects.all().order_by('-detected_time')
#             def parse_dt(value):
#                 try:
#                     dt = parse_datetime(value)
#                     if timezone.is_naive(dt):
#                         dt = timezone.make_aware(dt, timezone=timezone.utc)
#                     return dt
#                 except Exception as e:
#                     logger.warning(f"Invalid datetime input: {value} -> {e}")
#                     return None
#             start_dt = parse_dt(start_time) if start_time else None
#             end_dt = parse_dt(end_time) if end_time else None
#             if start_dt:
#                 queryset = queryset.filter(detected_time__gte=start_dt)
#             if end_dt:
#                 queryset = queryset.filter(detected_time__lte=end_dt)
#             if last_minutes:
#                 try:
#                     minutes = int(last_minutes)
#                     threshold = timezone.now() - timedelta(minutes=minutes)
#                     queryset = queryset.filter(detected_time__gte=threshold)
#                 except ValueError:
#                     return Response({"error": "last_minutes must be an integer"}, status=400)
#             if last_days:
#                 try:
#                     days = int(last_days)
#                     threshold = timezone.now() - timedelta(days=days)
#                     queryset = queryset.filter(detected_time__gte=threshold)
#                 except ValueError:
#                     return Response({"error": "last_days must be an integer"}, status=400)
#             if camera_id:
#                 queryset = queryset.filter(camera_id=camera_id)
        
#             # if visitor_id:
#             #     queryset = queryset.filter(visitors__id=visitor_id)
#             # if visitor_name:
#             #     queryset = queryset.filter(
#             #         Q(visitors__first_name__icontains=visitor_name) |
#             #         Q(visitors__last_name__icontains=visitor_name)
#             #   )
                
#             if visitor_id:
#                 queryset = queryset.filter(visitor_ids__contains=[visitor_id])

#             if visitor_name:
#                 visitor_matches = Visitor.objects.filter(
#                     Q(first_name__icontains=visitor_name) | Q(last_name__icontains=visitor_name)
#                 ).values_list('id', flat=True)
#                 queryset = queryset.filter(
#                     visitor_ids__overlap=list(visitor_matches)
#                 )

#             # Paginate standard list
#             paginator = self.pagination_class()
#             page = paginator.paginate_queryset(queryset, request)
#             serializer = VisitorEventHistorySerializer(page, many=True)
#             return paginator.get_paginated_response(serializer.data)
#         except Exception as e:
#             logger.exception("❌ Error in VisitorReportAPIView")
#             return Response({"error": "Internal Server Error"}, status=500)



# without many to many field ---->

# views.py
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta
from dateutil.parser import parse as parse_datetime
import logging

from .models import VisitorEventHistory, Visitor
from .serializers import VisitorEventHistorySerializer

logger = logging.getLogger(__name__)


class VisitorReportPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'


class VisitorReportAPIView(APIView):
    pagination_class = VisitorReportPagination

    def get(self, request):
        try:
            # Query params
            start_time = request.query_params.get('start_time')
            end_time = request.query_params.get('end_time')
            last_minutes = request.query_params.get('last_minutes')
            last_days = request.query_params.get('last_days')
            camera_id = request.query_params.get('camera_id')
            visitor_id = request.query_params.get('visitor_id')
            visitor_name = request.query_params.get('visitor_name')

            queryset = VisitorEventHistory.objects.all().order_by('-detected_time')

            # Parse datetimes safely
            def parse_dt(value):
                try:
                    dt = parse_datetime(value)
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone=timezone.utc)
                    return dt
                except Exception as e:
                    logger.warning(f"Invalid datetime input: {value} -> {e}")
                    return None

            # Time filtering
            if start_time:
                start_dt = parse_dt(start_time)
                if start_dt:
                    queryset = queryset.filter(detected_time__gte=start_dt)

            if end_time:
                end_dt = parse_dt(end_time)
                if end_dt:
                    queryset = queryset.filter(detected_time__lte=end_dt)

            if last_minutes:
                try:
                    threshold = timezone.now() - timedelta(minutes=int(last_minutes))
                    queryset = queryset.filter(detected_time__gte=threshold)
                except ValueError:
                    return Response({"error": "Invalid last_minutes"}, status=400)

            if last_days:
                try:
                    threshold = timezone.now() - timedelta(days=int(last_days))
                    queryset = queryset.filter(detected_time__gte=threshold)
                except ValueError:
                    return Response({"error": "Invalid last_days"}, status=400)

            if camera_id:
                queryset = queryset.filter(camera_id=camera_id)

            if visitor_id:
                queryset = [event for event in queryset if visitor_id in event.visitor_ids]

            if visitor_name:
                matched_visitors = Visitor.objects.filter(
                    Q(first_name__icontains=visitor_name) |
                    Q(last_name__icontains=visitor_name)
                ).values_list('id', flat=True)

                queryset = [event for event in queryset if any(v_id in event.visitor_ids for v_id in matched_visitors)]

            # Paginate & serialize
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            serializer = VisitorEventHistorySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            logger.exception("❌ Error in VisitorReportAPIView")
            return Response({"error": "Internal Server Error"}, status=500)




# # -----------------
# from rest_framework.pagination import PageNumberPagination
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from django.db.models import Q
# from django.utils import timezone
# from datetime import timedelta
# import logging
# import pytz
# from dateutil.parser import parse as parse_datetime

# from .serializers import VisitorEventHistorySerializer
# from .models import VisitorEventHistory

# logger = logging.getLogger(__name__)


# class VisitorReportPagination(PageNumberPagination):
#     page_size = 10
#     page_size_query_param = 'page_size'


# class VisitorReportAPIView(APIView):
#     pagination_class = VisitorReportPagination

#     def get(self, request):
#         try:
#             # Query params
#             start_time = request.query_params.get('start_time')
#             end_time = request.query_params.get('end_time')
#             last_minutes = request.query_params.get('last_minutes')
#             last_days = request.query_params.get('last_days')
#             camera_id = request.query_params.get('camera_id')
#             visitor_id = request.query_params.get('visitor_id')
#             visitor_name = request.query_params.get('visitor_name')

#             queryset = VisitorEventHistory.objects.prefetch_related('visitors').all()

#             # Parse datetime filters
#             def parse_dt(value):
#                 try:
#                     dt = parse_datetime(value, fuzzy=True)
#                     if timezone.is_naive(dt):
#                         dt = timezone.make_aware(dt, timezone=pytz.UTC)
#                     return dt
#                 except Exception as e:
#                     logger.warning(f"Invalid datetime format: {value} -> {e}")
#                     return None

#             start_dt = parse_dt(start_time) if start_time else None
#             end_dt = parse_dt(end_time) if end_time else None
#             threshold = None

#             if last_minutes:
#                 try:
#                     minutes = int(last_minutes)
#                     threshold = timezone.now() - timedelta(minutes=minutes)
#                 except ValueError:
#                     return Response({"error": "last_minutes must be an integer"}, status=400)

#             if last_days:
#                 try:
#                     days = int(last_days)
#                     threshold = timezone.now() - timedelta(days=days)
#                 except ValueError:
#                     return Response({"error": "last_days must be an integer"}, status=400)

#             # Apply direct DB filters
#             if camera_id:
#                 queryset = queryset.filter(camera_id=camera_id)

#             if visitor_id:
#                 queryset = queryset.filter(visitors__id=visitor_id)

#             if visitor_name:
#                 queryset = queryset.filter(
#                     Q(visitors__first_name__icontains=visitor_name) |
#                     Q(visitors__last_name__icontains=visitor_name)
#                 )

#             # In-memory filtering for capture_time and detected_time
#             filtered_events = []
#             for event in queryset:
#                 try:
#                     capture_dt = parse_datetime(event.capture_time, fuzzy=True)
#                     if timezone.is_naive(capture_dt):
#                         capture_dt = timezone.make_aware(capture_dt, timezone=pytz.UTC)
#                 except Exception as e:
#                     logger.warning(f"Skipping event {event.id} due to invalid capture_time: {e}")
#                     capture_dt = None

#                 include = True

#                 if start_dt:
#                     if event.detected_time < start_dt and (not capture_dt or capture_dt < start_dt):
#                         include = False

#                 if end_dt:
#                     if event.detected_time > end_dt and (capture_dt and capture_dt > end_dt):
#                         include = False

#                 if threshold:
#                     if event.detected_time < threshold and (not capture_dt or capture_dt < threshold):
#                         include = False

#                 if include:
#                     filtered_events.append(event)

#             # Final pagination
#             event_ids = [e.id for e in filtered_events]
#             final_queryset = VisitorEventHistory.objects.filter(id__in=event_ids).order_by('-detected_time')

#             paginator = self.pagination_class()
#             page = paginator.paginate_queryset(final_queryset, request)
#             serializer = VisitorEventHistorySerializer(page, many=True)
#             return paginator.get_paginated_response(serializer.data)

#         except Exception as e:
#             logger.exception("Unexpected error in VisitorReportAPIView")
#             return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
