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
from django.utils import timezone
from dateutil.parser import parse as parse_datetime


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

    # def get_role_from_token(self, token):
    #     try:
    #         decoded = jwt.decode(token,options={"verify_signature": False})
    #         return decoded.get("role")
    #     except jwt.DecodeError:
    #         return None


class VisitorAPIView(VisitorBaseView):
    pagination_class = VisitorPagination

    def get_queryset(self, request):
        show_deleted = request.query_params.get('show_deleted') == 'true'
        track_status = request.query_params.get('track_status')

        queryset = Visitor.all_objects.filter(is_deleted=True) if show_deleted else Visitor.objects.filter(is_deleted=False)

        if track_status is not None:
            if track_status.lower() == 'true':
                queryset = queryset.filter(track_status=True)
            elif track_status.lower() == 'false':
                queryset = queryset.filter(track_status=False)

        return queryset.order_by('-created_at')

    def get(self, request, pk=None):
        # token = self.get_token_from_header(request)
        # if not token or not self.is_token_valid(token):
        #     return Response({'error': 'Invalid or missing token'}, status=403)

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
        # token = self.get_token_from_header(request)
        # if not token or not self.is_token_valid(token):
        #     return Response({'error': 'Invalid or missing token'}, status=403)


        # visitor = Visitor.objects.create(
        #     first_name="abinnew",
        #     last_name="roy",
        #     email="john1.doe@example.com",
        #     phone_number="12345678901",
        #     gender="male",
        #     photo ="GOODDD.jpg"
        # )
        # return Response("creation done")

        serializer = VisitorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def put(self, request, pk):
        token = self.get_token_from_header(request)
        if not token or not self.is_token_valid(token):
            return Response({'error': 'Invalid or missing token'}, status=403)

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
        token = self.get_token_from_header(request)
        if not token or not self.is_token_valid(token):
            return Response({'error': 'Invalid or missing token'}, status=403)

        try:
            visitor = Visitor.all_objects.get(pk=pk)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=404)

        # role = self.get_role_from_token(token)
        role=2
        permanent = request.query_params.get('permanent') == 'true'

        if permanent:
            if role == 1:
                visitor.delete()
                return Response({'message': 'Visitor permanently deleted'}, status=200)
            return Response({'error': 'You are not allowed to permanently delete visitors.'}, status=403)
        
        # 🧠 Check if already soft-deleted
        if visitor.is_deleted:
            return Response({'error': 'Visitor is already soft-deleted.'}, status=409)

        visitor.soft_delete()
        return Response({'message': 'Visitor soft deleted'}, status=204)
    

class RestoreVisitorAPIView(VisitorBaseView):
    def post(self, request, pk):
        token = self.get_token_from_header(request)
        if not token or not self.is_token_valid(token):
            return Response({'error': 'Invalid or missing token'}, status=403)

        # role = self.get_role_from_token(token)
        role=1
        if role != 1:
            return Response({'error': 'You are not allowed to restore visitors.'}, status=403)

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


# the bellow code is perfect but now i want to try another way in above code


# class VisitorBaseView(APIView):
#     def get_token_from_header(self, request):
#         auth_header = request.META.get('HTTP_AUTHORIZATION', '')
#         if auth_header.startswith('Token ') or auth_header.startswith('Bearer '):
#             parts = auth_header.split(' ')
#             if len(parts) == 2:
#                 return parts[1]
#         return None

#     def is_token_valid(self, token):
#         url = "https://api.accelx.net/gd_apidev/user/token/verify/"  # Replace with your actual validation endpoint
#         try:
#             response = requests.post(url, json={"token": token})
#             return response.status_code == 200
#         except requests.RequestException as e:
#             print(f"Token validation request failed: {e}")
#             return False


# class VisitorListCreateAPIView(VisitorBaseView):
#     def get(self, request):
#         token = self.get_token_from_header(request)
#         print("Received token:", token)

#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         visitors = Visitor.all_objects.all().order_by('-created_at')

#         # Apply pagination
#         paginator = VisitorPagination()
#         result_page = paginator.paginate_queryset(visitors, request)
#         serializer = VisitorSerializer(result_page, many=True)
#         return paginator.get_paginated_response(serializer.data)

#     def post(self, request):
#         token = self.get_token_from_header(request)
#         print("Received token:", token)

#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         serializer = VisitorSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=201)
#         return Response(serializer.errors, status=400)


# class VisitorDetailAPIView(VisitorBaseView):
#     def get_object(self, pk):
#         try:
#             return Visitor.objects.get(pk=pk)
#         except Visitor.DoesNotExist:
#             return None

#     def get(self, request, pk):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         visitor = self.get_object(pk)
#         if not visitor:
#             return Response({'error': 'Visitor not found'}, status=404)

#         serializer = VisitorSerializer(visitor)
#         return Response(serializer.data)

#     def put(self, request, pk):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         visitor = self.get_object(pk)
#         if not visitor:
#             return Response({'error': 'Visitor not found'}, status=404)

#         serializer = VisitorSerializer(visitor, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=400)

#     def delete(self, request, pk):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         visitor = self.get_object(pk)
#         if not visitor:
#             return Response({'error': 'Visitor not found'}, status=404)

#         role = 1  # Update this as per your real logic
#         if role in [1, 2, 3, 4, 5]:
#             visitor.soft_delete()
#             return Response({'message': f'Visitor soft deleted by role {role}'}, status=204)
#         else:
#             return Response({'error': 'Unauthorized role'}, status=403)



# class TrackedVisitorAPIView(VisitorBaseView):
#     def get(self, request):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         tracked_visitors = Visitor.objects.filter(track_status=True).order_by('-created_at')
        
#         # Apply pagination
#         paginator = VisitorPagination()
#         result_page = paginator.paginate_queryset(tracked_visitors, request)
#         serializer = VisitorSerializer(result_page, many=True)
#         return paginator.get_paginated_response(serializer.data)


# class UntrackedVisitorAPIView(VisitorBaseView):
#     def get(self, request):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         untracked_visitors = Visitor.objects.filter(track_status=False).order_by('-created_at')

#         # Apply pagination
#         paginator = VisitorPagination()
#         result_page = paginator.paginate_queryset(untracked_visitors, request)
#         serializer = VisitorSerializer(result_page, many=True)
#         return paginator.get_paginated_response(serializer.data)

# class TrackedVisitorDetailAPIView(VisitorBaseView):
#     def get(self, request, pk):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         try:
#             tracked_visitor = Visitor.objects.get(pk=pk, track_status=True)
#         except Visitor.DoesNotExist:
#             return Response({'error': 'Soft-deleted visitor not found'}, status=404)
#         serializer = VisitorSerializer(tracked_visitor)
#         return Response(serializer.data, status=200)


# class UntrackedVisitorDetailAPIView(VisitorBaseView):
#     def get(self, request, pk):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         try:
#             untracked_visitor = Visitor.objects.get(pk=pk, track_status=False)
#         except Visitor.DoesNotExist:
#             return Response({'error': 'Soft-deleted visitor not found'}, status=404)
#         serializer = VisitorSerializer(untracked_visitor)
#         return Response(serializer.data, status=200)


# class VisitorActiveAPIView(VisitorBaseView):
#     def get(self, request):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         visitors = Visitor.objects.all().order_by('-created_at')

#         # Apply pagination
#         paginator = VisitorPagination()  # Assuming VisitorPagination is defined
#         result_page = paginator.paginate_queryset(visitors, request)
#         serializer = VisitorSerializer(result_page, many=True)
#         return paginator.get_paginated_response(serializer.data)


# class SoftDeleteVisitorListAPIView(VisitorBaseView):
#     def get(self, request):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         deleted_visitors = Visitor.all_objects.filter(is_deleted=True).order_by('-created_at')

#         # Apply pagination
#         paginator = VisitorPagination()  # Assuming VisitorPagination is defined
#         result_page = paginator.paginate_queryset(deleted_visitors, request)
#         serializer = VisitorSerializer(result_page, many=True)
#         return paginator.get_paginated_response(serializer.data)


# class SoftDeleteVisitorDetailAPIView(VisitorBaseView):
#     def get(self, request, pk):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         try:
#             visitor = Visitor.all_objects.get(pk=pk, is_deleted=True)
#         except Visitor.DoesNotExist:
#             return Response({'error': 'Soft-deleted visitor not found'}, status=404)
#         serializer = VisitorSerializer(visitor)
#         return Response(serializer.data)


# class RestoreVisitorAPIView(VisitorBaseView):
#     def post(self, request, pk):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         role = 2  # Replace this with real logic from token/user
#         if role != 1:
#             return Response({'error': 'You are not allowed to restore visitors.'}, status=403)

#         try:
#             visitor = Visitor.all_objects.get(pk=pk, is_deleted=True)
#         except Visitor.DoesNotExist:
#             return Response({'error': 'Soft-deleted visitor not found'}, status=404)

#         visitor.restore()
#         return Response({'message': 'Visitor restored successfully'}, status=200)


# class PermanentDeleteVisitorAPIView(VisitorBaseView):
#     def delete(self, request, pk):
#         token = self.get_token_from_header(request)
#         if not token or not self.is_token_valid(token):
#             return Response({'error': 'Invalid or missing token'}, status=403)

#         role = 2  # Replace this with role extracted from the token
#         if role != 1:
#             return Response({'error': 'You are not allowed to permanently delete visitors.'}, status=403)

#         try:
#             visitor = Visitor.all_objects.get(pk=pk)
#         except Visitor.DoesNotExist:
#             return Response({'error': 'Visitor not found'}, status=404)

#         visitor.delete()
#         return Response({'message': 'Visitor permanently deleted'}, status=200)




# class VisitorTrackAPIView(APIView):
#     def get_token_from_header(self, request):
#         auth_header = request.META.get('HTTP_AUTHORIZATION', '')
#         if auth_header.startswith('Bearer ') or auth_header.startswith('Token '):
#             return auth_header.split(' ')[1]
#         return None

#     def decode_token(self, token):
#         try:
#             payload = jwt.decode(token, options={"verify_signature": False})
#             return payload
#         except jwt.ExpiredSignatureError:
#             return {'error': 'Token expired'}
#         except jwt.InvalidTokenError:
#             return {'error': 'Invalid token'}

#     def get(self, request):
#         access_token = self.get_token_from_header(request)
#         if not access_token:
#             return Response({'error': 'Token not provided'}, status=status.HTTP_401_UNAUTHORIZED)

#         decoded = self.decode_token(access_token)
#         if 'error' in decoded:
#             return Response(decoded, status=status.HTTP_403_FORBIDDEN)

#         institute_id = decoded.get('institute')
#         if not institute_id:
#             return Response({'error': 'Institute ID not found in token'}, status=400)

#         # 📌 Specific camera ID
#         camera_id = 119  # <-- you can later accept this dynamically via query params or path
#         camera_detail_url = f"https://api.accelx.net/gd_apidev/camera/camera-setups/{camera_id}/?institute={institute_id}"
#         headers = {
#             'Authorization': f"Bearer {access_token}"
#         }

#         try:
#             response = requests.get(camera_detail_url, headers=headers)
#             if response.status_code == 200:
#                 camera_data = response.json()
#                 return Response({
#                     'institute_id': institute_id,
#                     'camera': camera_data
#                 }, status=200)
#             else:
#                 return Response({'error': 'Failed to fetch camera detail'}, status=response.status_code)
#         except requests.RequestException as e:
#             return Response({'error': str(e)}, status=500)


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
            capture_time_str = request.data.get("capture_time")
            manual_visitor_ids = request.data.get("visitor_ids")  # Manual test support

            if not (camera_id and token and capture_time_str):
                return Response({"error": "Missing camera_id, token, or capture_time"}, status=status.HTTP_400_BAD_REQUEST)

            # Convert capture_time
            try:
                capture_time = timezone.datetime.fromisoformat(capture_time_str)
            except Exception:
                return Response({"error": "Invalid capture_time format"}, status=400)

            # ✅ Manual test path (ML server bypass)
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

            # ✅ ML server flow
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

            # Send visitor images to ML server
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
            capture_time=capture_time
            print(capture_time)
            detected_time = timezone.now()
            visitor_ids = [str(visitor.id) for visitor in visitors]
            # camera_info = self.get_camera_info(camera_id, token)
           
            # if not camera_info:
            #     logger.error(f"Camera info not found for camera_id {camera_id}")
            #     return Response({"error": "Camera info not available"}, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"➡️ Creating VisitorEventHistory for camera {camera_id}, visitors {visitor_ids}")
        
            event = VisitorEventHistory.objects.create(
                visitor_ids=visitor_ids,
                camera_id=camera_id,
                snapshot_url="https://default.snapshot",
                capture_time=capture_time,
                detected_time=detected_time,
            )
        except Exception as e:
            logger.error(f"Error creating event or WebSocket send: {e}")
        finally:
            clear_request_token()  # 👈 Always clear
    


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

import base64
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Visitor, VisitorEventHistory

class VisitorDetectionsAPIView(APIView):
    def get(self, request, visitor_id, *args, **kwargs):
        # ✅ Get visitor object or return 404
        visitor = get_object_or_404(Visitor, pk=visitor_id)

        # ✅ Get detections where this visitor's UID appears
        detections = VisitorEventHistory.objects.filter(
            visitor_ids__contains=[str(visitor.uid)]
        ).order_by('-detected_time')

        if not detections.exists():
            return Response({"detail": "No detections found for this visitor."}, status=status.HTTP_404_NOT_FOUND)

        results = []
        for detection in detections:
            try:
                # Read and encode image to base64
                image_url = detection.snapshot_url
                if image_url:
                    import requests
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        image_data = base64.b64encode(img_response.content).decode('utf-8')
                        base64_image = f"data:image/jpeg;base64,{image_data}"
                    else:
                        base64_image = None
                else:
                    base64_image = None
            except Exception:
                base64_image = None

            results.append({
                "detection_id": detection.id,
                "cam_id": detection.camera_id,
                "location": detection.camera_location,
                "lat": detection.latitude,
                "long": detection.longitude,
                "detected_time": detection.detected_time.isoformat(),
                "exit_time": detection.capture_time.isoformat(),
                "image": base64_image
            })

        return Response(results, status=status.HTTP_200_OK)
