from django.urls import path
from .views import VisitorTrackingAPIView,LoginApiView,CameraListAPIView,VisitorListCreateAPIView, VisitorDetailAPIView

urlpatterns = [
    path('gateway/', VisitorTrackingAPIView.as_view(),name='visitor_tracking'),
    path('api/login/', LoginApiView.as_view()),
    path('api/cameras/', CameraListAPIView.as_view()),
    path('api/visitor/', VisitorListCreateAPIView.as_view(), name='visitor-list-create'),
    path('api/visitor/<int:pk>/', VisitorDetailAPIView.as_view(), name='visitor-detail'),
]