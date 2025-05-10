from django.shortcuts import render
import requests
import jwt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# Create your views here.
from .models import Visitor,VisitorEventHistory
from .serializers import VisitorSerializer
from rest_framework.permissions import IsAuthenticated
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
        # token = self.get_token_from_header(request)
        # print(f"this is token test->{token}")
        # if not token or not self.is_token_valid(token):
        #     return Response({'error': 'Invalid or missing token'}, status=403)
        if pk:
            try:
                visitor = Visitor.all_objects.get(pk=pk)
            except Visitor.DoesNotExist:
                return Response({'error': 'Visitor not found'}, status=404)
            serializer = VisitorSerializer(visitor)
            # print(visitor.photo.url)
            return Response(serializer.data)
        queryset = self.get_queryset(request)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = VisitorSerializer(page, many=True)
        # for visitor in page:
        #     if visitor.photo:
        #         print("Photo URL:", visitor.photo.url)
        # photo_url=visitor.photo
        # print(photo_url)
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        # token = self.get_token_from_header(request)
        # if not token or not self.is_token_valid(token):
        #     return Response({'error': 'Invalid or missing token'}, status=403)

        photo = request.FILES.get('photo')

        # Collect and validate input
        visitor_fields = {
            "first_name": request.data.get('first_name'),
            "last_name": request.data.get('last_name'),
            "email": request.data.get('email'),
            "phone_number": request.data.get('phone_number'),
            "gender": request.data.get('gender'),
            "photo": photo,
            'face_detect': request.data.get('face_detect', True),
        }

        # Check required fields manually before serializer
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

            # Avoid default Django storage
            serializer.validated_data.pop('photo', None)

            try:
                visitor = serializer.save()
            except Exception as e:
                return Response({"error": f"Database save failed: {str(e)}"}, status=500)

            if file_key:
                visitor.photo.name = file_key
                visitor.save()

            return Response(VisitorSerializer(visitor).data, status=201)

        return Response(serializer.errors, status=400)
    def put(self, request, pk):
        # token = self.get_token_from_header(request)
        # if not token or not self.is_token_valid(token):
        #     return Response({'error': 'Invalid or missing token'}, status=403)
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
        # token = self.get_token_from_header(request)
        # if not token or not self.is_token_valid(token):
        #     return Response({'error': 'Invalid or missing token'}, status=403)
        try:
            visitor = Visitor.all_objects.get(pk=pk)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=404)
        # role = self.get_role_from_token(token)
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
        # token = self.get_token_from_header(request)
        # if not token or not self.is_token_valid(token):
        #     return Response({'error': 'Invalid or missing token'}, status=403)
        Response({'error': 'You are not allowed to restore visitors.'}, status=403)
        try:
            visitor = Visitor.all_objects.get(pk=pk, is_deleted=True)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found or not deleted'}, status=404)
        visitor.restore()
        return Response({'message': 'Visitor restored successfully'}, status=200)







# # views.py

# class VisitorTypeAPIView(APIView):
#     def get(self, request):
#         token = VisitorBaseView().get_token_from_header(request)
#         if not token or not VisitorBaseView().is_token_valid(token):
#             return Response({'error': 'You are not authorized to perform this action.'}, status=403)

#         types = [
#             {"id": choice[0], "type": choice[1]}
#             for choice in Visitor.VISITOR_TYPE_CHOICES
#         ]
#         return Response(types, status=200)


# views.py (add this below your VisitorAPIView or in the same file)

# class VisitorTypeListAPIView(VisitorBaseView):
#     def get(self, request):
#         # token = self.get_token_from_header(request)
#         # if not token or not self.is_token_valid(token):
#         #     return Response({'error': 'You are not authorized to perform this action.'}, status=403)

#         types = [{"id": key, "type": label} for key, label in Visitor.VISITOR_TYPE_CHOICES]
#         return Response(types, status=200)


from .serializers import VisitorWithTypeSerializer
import difflib

class VisitorTypeListAPIView(APIView):
    def get(self, request):
        visitor_type_param = request.query_params.get('visitor_type')
        visitors = Visitor.all_objects.all()

        if visitor_type_param:
            type_ids = [t.strip().lower() for t in visitor_type_param.split(',')]
            valid_ids = [choice[0] for choice in Visitor.VISITOR_TYPE_CHOICES]

            invalid_ids = [t for t in type_ids if t not in valid_ids]

            if invalid_ids:
                suggestions = {
                    invalid: difflib.get_close_matches(invalid, valid_ids, n=1)
                    for invalid in invalid_ids
                }

                error_response = {
                    "error": "One or more invalid visitor_type values.",
                    "invalid_values": invalid_ids,
                    "did_you_mean": {k: v[0] if v else None for k, v in suggestions.items()}
                }
                return Response(error_response, status=status.HTTP_400_BAD_REQUEST)

            visitors = visitors.filter(visitor_type__in=type_ids)

        serializer = VisitorWithTypeSerializer(visitors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class VisitorDetailWithTypeAPIView(APIView):
    def get(self, request, pk):
        try:
            visitor = Visitor.all_objects.get(pk=pk)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = VisitorWithTypeSerializer(visitor)
        return Response(serializer.data, status=status.HTTP_200_OK)



class VisitorTrackAPIView(APIView):
    def get_token_from_header(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token ') or auth_header.startswith('Bearer '):
            parts = auth_header.split(' ')
            if len(parts) == 2:
                return parts[1]
        return None

    def get(self, request):
        token = self.get_token_from_header(request)
        if not token:
            return Response({'error': 'Missing token'}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Decode the token without verifying the signature
            payload = jwt.decode(token, options={"verify_signature": False})
            institute_id = payload.get('institute')
        except jwt.DecodeError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

        if not institute_id:
            return Response({'error': 'Institute not found in token'}, status=status.HTTP_404_NOT_FOUND)

        # External camera API call (POST)
        try:
            camera_api_url = "https://api.accelx.net/gd_apidev/camera/camera-setups/133/"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            # payload = {'institute': institute_id}

            response = requests.get(camera_api_url, headers=headers)

            if response.status_code != 200:
                return Response({
                    'error': 'Failed to fetch camera details',
                    'status_code': response.status_code,
                    'response_text': response.text  # Debug info
                }, status=response.status_code)

            camera_data = response.json()
        except requests.RequestException as e:
            return Response({'error': f'Request failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'camera_details': camera_data}, status=status.HTTP_200_OK)


# ===============================================================
class LoginApiView(APIView):
    def post(self,request):
        payload = request.data
        print("===== Incoming Request =====")
        print("Payload:", payload)
        print("============================")
        login_url = 'https://api.accelx.net/gd_apidev/user/login/'

        try :
            response = requests.post(login_url,json=payload)
            response.raise_for_status()
            login_data =response.json()
            access_token = login_data.get('access')
            if not access_token:
                return Response({'error':'Access Token not Received'},status=401)
            return Response({
                'access_token':access_token
            },status=200)
        except requests.exceptions.RequestException as e:
            return Response({'error': str(e)}, status=502)
        

class CameraListAPIView(APIView):
    def post(self,request):
        access_Token = request.data.get('access_token')
        # print(f"this is access token{access_Token}")

        if not access_Token:
            return Response({'error': 'Access token required'},status=400)
        
        try:
            decoded_token = jwt.decode(access_Token, options={"verify_signature": False})
            institute= decoded_token.get('institute')
            user_id = decoded_token.get('user_id')
            username = decoded_token.get('name')
            role = decoded_token.get('role')
            print("Decoded JWT Token:")
            print("User ID:", user_id)
            print("Username:", username)
            print("Role:", role)
            print('Institute:',institute)

            if not institute:
                return Response({'error':'Institute Id not found in token'},status=400)
            
            camera_list_url=f"https://api.accelx.net/gd_apidev/camera/camera-setups/?institute={institute}"
            headers={
                'Authorization': f"Bearer {access_Token}"
            }
            camera_response=requests.get(camera_list_url,headers=headers)
            camera_response.raise_for_status()
            return Response(camera_response.json(),status=200)
        except jwt.DecodeError:
            return Response({'error':'Invalid Token'},status=401)
        except requests.exceptions.RequestException as e:
            return Response({'error':str(e)},status=502)

            




class VisitorTrackingAPIView(APIView):
    def post(self,request):
        auth_token = request.headers.get('Authorization')
        payload = request.data
     
        # test
        print("===== Incoming Request =====")
        print("Authorization Header:", auth_token)
        print("Payload:", payload)
        print("============================")

        # Set headers for forward this into existing api server.
        headers = {
        # 'Authorization': auth_token,
        'Content-Type': 'application/json'
        }
        # Existing api server endpoint
        exisiting_api_login_url = 'https://api.accelx.net/gd_apidev/user/login/'
        ml_server_url = 'ml endpoint'
        try:
            # send it into login url
            response = requests.post(exisiting_api_login_url,json=payload)
            response.raise_for_status()
            login_data = response.json()
            Access_Token = login_data.get('access')
            print("Access Token:", Access_Token)
            if not Access_Token:
                return Response({'error': 'Access token not found.'}, status=status.HTTP_401_UNAUTHORIZED)
            
            #Decode the token (without verifying signature for now)
            decoded_token = jwt.decode(Access_Token, options={"verify_signature": False})

            #Extract fields
            user_id = decoded_token.get('user_id')
            username = decoded_token.get('name')
            role = decoded_token.get('role')
            institute= decoded_token.get('institute')

            print("Decoded JWT Token:")
            print("User ID:", user_id)
            print("Username:", username)
            print("Role:", role)
            print('Institute:',institute)

            #Call Camera list api to view all camera with institute id
            if institute:
                camera_list_url=f"https://api.accelx.net/gd_apidev/camera/camera-setups/?institute={institute}"
                camera_list_headers={
                    'Authorization': f"Bearer {Access_Token}"
                }
                camera_list_response= requests.get(camera_list_url,headers=camera_list_headers)
                camera_list_response.raise_for_status()
                camera_list_data = camera_list_response.json()
            else:
                camera_list_data = {"error": "Institute ID not found in token."}
                

            
            print("Response from Existing API")
            print(response.json())
            print("Response from camera list api")
            print(camera_list_response.json())
            return Response({
                'status': 'success',
                'external_response': response.json(),
                'camera_data':camera_list_response.json()
                
            }, status=status.HTTP_200_OK)

        # demo test
        except requests.exceptions.RequestException as e:
            # return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
            print("EXCEPTION CAUGHT")
            print(str(e))
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        #     # -------------------------
        #     # Extract frame from response (update based on actual structure)
        #     frame_data = response.json().get('frame')

        #     # if there is no frame then return frame not found
        #     if not frame_data:
        #         return Response({'error': 'Frame not found in existing API response'},status=400)
            
        #     # send frame to ml server
        #     ml_payload={
        #         'frame': frame_data
        #     }
        #     ml_response = requests.post(ml_server_url,json=ml_payload)
        #     ml_response.raise_for_status()
        #     print("ML Server Response")
        #     print(ml_response.json())

        #     return Response(ml_response.json(), status=ml_response.status_code)
        
        # except requests.exceptions.RequestException as e:
        #     # return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        #     print("EXCEPTION CAUGHT")
        #     print(str(e))
        #     return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# 3 function------------------------------------------>
# import base64
# import logging
# import requests
# from io import BytesIO
# from PIL import Image

# from django.utils import timezone
# from django.core.files.uploadedfile import SimpleUploadedFile

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status

# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync

# from .models import Visitor, VisitorEventHistory

# logger = logging.getLogger(__name__)

# class MLDetectionAPIView(APIView):
#     def post(self, request, *args, **kwargs):
#         try:
#             frame = request.data.get("frame")
#             camera_id = request.data.get("camera_id")
#             token = request.data.get("token")
#             capture_time_str = request.data.get("capture_time")

#             if not (frame and camera_id and token and capture_time_str):
#                 return Response({"error": "Missing frame, camera_id, token or capture_time"}, status=status.HTTP_400_BAD_REQUEST)

#             capture_time = timezone.datetime.fromisoformat(capture_time_str)

#             response = self.send_to_ml_server(frame, camera_id, token, capture_time)

#             if response.get("status") == "success":
#                 return Response(response, status=status.HTTP_200_OK)
#             else:
#                 return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         except Exception as e:
#             logger.error(f"Error in ML detection view: {e}")
#             return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def send_to_ml_server(self, frame, camera_id, token, capture_time):
#         try:
#             frame_data = base64.b64decode(frame)
#             img_file = SimpleUploadedFile("frame.jpg", frame_data, content_type="image/jpeg")

#             visitor_files = []
#             visitors = Visitor.objects.filter(is_deleted=False, photo__isnull=False)
#             for visitor in visitors:
#                 try:
#                     with visitor.photo.open('rb') as photo_file:
#                         visitor_files.append(
#                             ('visitor_images', (f"{visitor.uid}.jpg", photo_file.read(), 'image/jpeg'))
#                         )
#                 except Exception as e:
#                     logger.warning(f"Error reading visitor image: {e}")

#             files = [('frame', img_file)] + visitor_files
#             response = requests.post("http://mlserver.com/detect", files=files, data={'camera_id': camera_id, 'token': token})

#             if response.status_code == 200:
#                 detection_data = response.json()
#                 visitor_ids = detection_data.get('visitor_ids', [])
#                 if visitor_ids:
#                     matched_visitors = Visitor.objects.filter(uid__in=visitor_ids)
#                     self.create_event(matched_visitors, camera_id, token, capture_time)
#                     return {"status": "success", "message": "Visitors detected", "visitor_ids": visitor_ids}
#                 else:
#                     return {"status": "error", "message": "No visitors detected"}
#             else:
#                 return {"status": "error", "message": "ML server error"}
#         except Exception as e:
#             logger.error(f"Error sending to ML server: {e}")
#             return {"status": "error", "message": "Error contacting ML server"}

#     def create_event(self, visitors, camera_id, token, capture_time):
#         try:
#             detected_time = timezone.now()
#             visitor_ids = [visitor.uid for visitor in visitors]

#             camera_info = self.get_camera_info(camera_id, token)
#             if not camera_info:
#                 return

#             event = VisitorEventHistory.objects.create(
#                 visitor_ids=visitor_ids,
#                 camera_id=camera_id,
#                 camera_location=camera_info.get("location_name"),
#                 latitude=camera_info.get("latitude"),
#                 longitude=camera_info.get("longitude"),
#                 snapshot_url=camera_info.get("snapshot_url", "https://default.snapshot"),
#                 capture_time=capture_time,
#                 detected_time=detected_time,
#                 institute=camera_info.get("institute"),
#                 camera_model=camera_info.get("camera_model"),
#                 video_server_ip=camera_info.get("video_server_ip"),
#                 video_server_port=camera_info.get("video_server_port"),
#             )

#             # WebSocket notification
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 "visitor_events",
#                 {
#                     "type": "event.message",
#                     "message": {
#                         "event": "visitor_detected",
#                         "camera_id": event.camera_id,
#                         "location": event.camera_location,
#                         "visitor_ids": event.visitor_ids,
#                         "detected_time": event.detected_time.isoformat(),
#                         "capture_time": event.capture_time.isoformat(),
#                         "snapshot_url": event.snapshot_url,
#                     }
#                 }
#             )

#             logger.info("WebSocket message sent for VisitorEventHistory")

#         except Exception as e:
#             logger.error(f"Error creating VisitorEventHistory or sending WebSocket: {e}")

#     def get_camera_info(self, camera_id, token):
#         try:
#             camera_api_url = f"https://api.accelx.net/gd_apidev/camera/camera-setups/133/"
#             headers = {
#                 'Authorization': f'Bearer {token}',
#                 'Content-Type': 'application/json'
#             }

#             response = requests.get(camera_api_url, headers=headers)

#             if response.status_code == 200:
#                 camera_data = response.json()
#                 return {
#                     'latitude': camera_data.get('latitude'),
#                     'longitude': camera_data.get('longitude'),
#                     'location_name': camera_data.get('location_name'),
#                     'snapshot_url': camera_data.get('url'),
#                     'institute': camera_data.get('institute'),
#                     'camera_model': camera_data.get('model'),
#                     'video_server_ip': camera_data.get('video_server_ip'),
#                     'video_server_port': camera_data.get('video_server_port'),
#                 }
#             else:
#                 logger.error(f"Failed to fetch camera details: {response.status_code}")
#                 return None
#         except requests.RequestException as e:
#             logger.error(f"Error calling external camera API: {e}")
#             return None



# MANUAL TEST-------bellow manual test works fine but here i use visitor uid now try with id

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
            # try:
            #     capture_time = capture_time
            # except Exception:
            #     return Response({"error": "Invalid capture_time format"}, status=400)
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

            logger.info(f"➡️ Creating VisitorEventHistory for camera {camera_id}")
            event = VisitorEventHistory.objects.create(
                visitor_ids=[],  # Temp empty; will update later
                camera_id=camera_id,
                snapshot_url=snapshot_url,
                capture_time=capture_time,
                detected_time=detected_time,
            )
            event.visitors.set(visitors)  # This triggers m2m_changed
        except Exception as e:
            logger.error(f"Error creating event or WebSocket send: {e}")
        finally:
            clear_request_token()



# # Manual test try with visitor id------->>>>>
        
# import base64
# import logging
# import requests
# from io import BytesIO
# from PIL import Image

# from django.utils import timezone
# from django.core.files.uploadedfile import SimpleUploadedFile

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status

# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
# from myapp.utils import set_request_token, clear_request_token
# from .models import Visitor, VisitorEventHistory
# logger = logging.getLogger(__name__)

# class MLDetectionAPIView(APIView):
#     def post(self, request, *args, **kwargs):
#         try:
#             frame = request.data.get("frame")
#             camera_id = request.data.get("camera_id")
#             token = request.headers.get("Authorization")
#             if token and token.startswith("Bearer "):
#                 token = token[len("Bearer "):]
#             capture_time_str = request.data.get("capture_time")
#             manual_visitor_ids = request.data.get("visitor_ids")  # Manual test support

#             if not (camera_id and token and capture_time_str):
#                 return Response({"error": "Missing camera_id, token, or capture_time"}, status=status.HTTP_400_BAD_REQUEST)

#             # Convert capture_time
#             try:
#                 capture_time = timezone.datetime.fromisoformat(capture_time_str)
#             except Exception:
#                 return Response({"error": "Invalid capture_time format"}, status=400)

#             # ✅ Manual test path (ML server bypass)
#             if manual_visitor_ids:
#                 visitors = Visitor.objects.filter(id__in=manual_visitor_ids)
#                 if not visitors.exists():
#                     return Response({"error": "No valid visitors found"}, status=404)

#                 try:
#                     self.create_event(visitors, camera_id, token, capture_time)
#                     return Response({
#                         "status": "success",
#                         "message": "Manual test: event created",
#                         "visitor_ids": manual_visitor_ids
#                     }, status=200)
#                 except Exception as e:
#                     return Response({"error": str(e)}, status=400)

#             # ✅ ML server flow
#             if not frame:
#                 return Response({"error": "Missing frame for ML processing"}, status=400)

#             return Response(self.send_to_ml_server(frame, camera_id, token, capture_time))

#         except Exception as e:
#             logger.error(f"Error in ML detection view: {e}")
#             return Response({"error": "Internal server error"}, status=500)

#     def send_to_ml_server(self, frame, camera_id, token, capture_time):
#         try:
#             frame_data = base64.b64decode(frame)
#             img_file = SimpleUploadedFile("frame.jpg", frame_data, content_type="image/jpeg")

#             # Send visitor images to ML server
#             visitor_files = []
#             for visitor in Visitor.objects.filter(is_deleted=False, photo__isnull=False):
#                 try:
#                     with visitor.photo.open('rb') as photo_file:
#                         visitor_files.append(
#                             ('visitor_images', (f"{visitor.id}.jpg", photo_file.read(), 'image/jpeg'))
#                         )
#                 except Exception as e:
#                     logger.warning(f"Error reading visitor image: {e}")

#             files = [('frame', img_file)] + visitor_files
#             response = requests.post("http://mlserver.com/detect", files=files, data={'camera_id': camera_id, 'token': token})

#             if response.status_code == 200:
#                 detection_data = response.json()
#                 visitor_ids = detection_data.get('visitor_ids', [])
#                 if visitor_ids:
#                     visitors = Visitor.objects.filter(id__in=visitor_ids)
#                     self.create_event(visitors, camera_id, token, capture_time)
#                     return {"status": "success", "visitor_ids": visitor_ids}
#                 return {"status": "error", "message": "No visitors detected"}
#             return {"status": "error", "message": "ML server error"}
#         except Exception as e:
#             logger.error(f"ML server communication error: {e}")
#             return {"status": "error", "message": "Error contacting ML server"}

#     def create_event(self, visitors, camera_id, token, capture_time):
#         try:
#             set_request_token(token)
#             detected_time = timezone.now()
#             visitor_ids = [str(visitor.id) for visitor in visitors]  # ✅ Use default primary key

#             logger.info(f"➡️ Creating VisitorEventHistory for camera {camera_id}, visitors {visitor_ids}")

#             event = VisitorEventHistory.objects.create(
#                 visitor_ids=visitor_ids,
#                 camera_id=camera_id,
#                 snapshot_url="https://default.snapshot",
#                 capture_time=capture_time,
#                 detected_time=detected_time,
#             )
#         except Exception as e:
#             logger.error(f"Error creating event or WebSocket send: {e}")
#         finally:
#             clear_request_token()  # ✅ Always clear





# ------------------------------Camera Detection Detail for visitor 
            


# import base64
# import requests
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from .models import Visitor, VisitorEventHistory

# class VisitorDetectionsAPIView(APIView):
#     def get(self, request, visitor_id):
#         try:
#             visitor = Visitor.objects.filter(id=visitor_id, is_deleted=False).first()
#             if not visitor:
#                 return Response({"error": "Visitor not found"}, status=status.HTTP_404_NOT_FOUND)

#             # ✅ Search for detections containing the visitor's UID in the JSONField
#             detections = VisitorEventHistory.objects.filter(visitor_ids__contains=[str(visitor.uid)]).order_by('-detected_time')

#             if not detections.exists():
#                 return Response([], status=status.HTTP_404_NOT_FOUND)

#             response_data = []
#             for detection in detections:
#                 image_base64 = ""
#                 try:
#                     img_response = requests.get(detection.snapshot_url)
#                     if img_response.status_code == 200:
#                         encoded = base64.b64encode(img_response.content).decode('utf-8')
#                         image_base64 = f"data:image/jpeg;base64,{encoded}"
#                 except Exception:
#                     pass  # If image fetch fails, leave it blank

#                 response_data.append({
#                     "detection_id": f"detect-{detection.id}",
#                     "cam_id": detection.camera_id,
#                     "location": detection.camera_location,
#                     "lat": detection.latitude,
#                     "long": detection.longitude,
#                     "detected_time": detection.detected_time.isoformat(),
#                     "exit_time": None,  # Optional: update if available
#                     "image": image_base64,
#                 })

#             return Response(response_data, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# -------------------------------------------------




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
                visitor_first_names = [v.first_name for v in d.visitors.all()]
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

#     # chat----->
    
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Count
from django.db.models.functions import TruncHour, TruncDay
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
            # Get query params
            start_time = request.query_params.get('start_time')
            end_time = request.query_params.get('end_time')
            last_minutes = request.query_params.get('last_minutes')
            last_days = request.query_params.get('last_days')
            camera_id = request.query_params.get('camera_id')
            visitor_id = request.query_params.get('visitor_id')
            visitor_name = request.query_params.get('visitor_name')
            group_by = request.query_params.get('group_by')  # 'hour' or 'day'

            # Base queryset
            queryset = VisitorEventHistory.objects.prefetch_related('visitors').all().order_by('-detected_time')

            # Helper: parse datetime safely
            def parse_dt(value):
                try:
                    dt = parse_datetime(value)
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone=timezone.utc)
                    return dt
                except Exception as e:
                    logger.warning(f"Invalid datetime input: {value} -> {e}")
                    return None

            # Time filters
            start_dt = parse_dt(start_time) if start_time else None
            end_dt = parse_dt(end_time) if end_time else None

            if start_dt:
                queryset = queryset.filter(detected_time__gte=start_dt)

            if end_dt:
                queryset = queryset.filter(detected_time__lte=end_dt)

            if last_minutes:
                try:
                    minutes = int(last_minutes)
                    threshold = timezone.now() - timedelta(minutes=minutes)
                    queryset = queryset.filter(detected_time__gte=threshold)
                except ValueError:
                    return Response({"error": "last_minutes must be an integer"}, status=400)

            if last_days:
                try:
                    days = int(last_days)
                    threshold = timezone.now() - timedelta(days=days)
                    queryset = queryset.filter(detected_time__gte=threshold)
                except ValueError:
                    return Response({"error": "last_days must be an integer"}, status=400)

            if camera_id:
                queryset = queryset.filter(camera_id=camera_id)
            
            if visitor_id:
                queryset = queryset.filter(visitors__id=visitor_id)

            if visitor_name:
                queryset = queryset.filter(
                    Q(visitors__first_name__icontains=visitor_name) |
                    Q(visitors__last_name__icontains=visitor_name)
                )

            # Paginate standard list
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
