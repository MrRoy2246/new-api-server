from django.shortcuts import render
import requests
import jwt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# Create your views here.

from .models import Visitor
from .serializers import VisitorSerializer

class VisitorListCreateAPIView(APIView):
    def get(self, request):
        visitors = Visitor.objects.all().order_by('-created_at')
        serializer = VisitorSerializer(visitors, many=True)
        return Response(serializer.data, status=200)

    def post(self, request):
        serializer = VisitorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class VisitorDetailAPIView(APIView):
    def get_object(self, pk):
        try:
            return Visitor.objects.get(pk=pk)
        except Visitor.DoesNotExist:
            return None

    def get(self, request, pk):
        visitor = self.get_object(pk)
        if not visitor:
            return Response({'error': 'Visitor not found'}, status=404)
        serializer = VisitorSerializer(visitor)
        return Response(serializer.data)

    def put(self, request, pk):
        visitor = self.get_object(pk)
        if not visitor:
            return Response({'error': 'Visitor not found'}, status=404)
        serializer = VisitorSerializer(visitor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        visitor = self.get_object(pk)
        if not visitor:
            return Response({'error': 'Visitor not found'}, status=404)
        visitor.delete()
        return Response({'message': 'Visitor deleted'}, status=204)


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
            camera_response=requests.get(camera_list_url)
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
