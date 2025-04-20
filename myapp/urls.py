from django.urls import path
from .views import VisitorTrackingAPIView,LoginApiView,CameraListAPIView,VisitorListCreateAPIView, VisitorDetailAPIView,VisitorReportAPIView,SoftDeleteVisitorListAPIView,SoftDeleteVisitorDetailAPIView,RestoreVisitorAPIView,TrackedVisitorDetailAPIView,TrackedVisitorAPIView,UntrackedVisitorAPIView,UntrackedVisitorDetailAPIView,PermanentDeleteVisitorAPIView

urlpatterns = [
    path('gateway/', VisitorTrackingAPIView.as_view(),name='visitor_tracking'),
    path('api/login/', LoginApiView.as_view()),
    path('api/cameras/', CameraListAPIView.as_view()),
    path('api/visitor/', VisitorListCreateAPIView.as_view(), name='visitor-list-create'),
    path('api/visitor/<int:pk>/', VisitorDetailAPIView.as_view(), name='visitor-detail'),


    path('api/visitor/track/', TrackedVisitorAPIView.as_view(), name='track-visitor-list'),
    path('api/visitor/track/<int:pk>/', TrackedVisitorDetailAPIView.as_view(), name='track-visitor-detail'),
    
    
    path('api/visitor/untrack/', UntrackedVisitorAPIView.as_view(), name='untrack-visitor-list'),
    path('api/visitor/untrack/<int:pk>/', UntrackedVisitorDetailAPIView.as_view(), name='untrack-visitor-detail'),

    path('api/visitor/report/', VisitorReportAPIView.as_view(), name='visitor-report'),
    path('api/visitor/soft/', SoftDeleteVisitorListAPIView.as_view(), name='soft-visitor-list'),
    path('api/visitor/soft/<int:pk>/', SoftDeleteVisitorDetailAPIView.as_view(), name='soft-visitor-report'),
    path('api/visitor/restore/<int:pk>/', RestoreVisitorAPIView.as_view(), name='restore-visitor'),

    path('api/visitor/delete/<int:pk>/', PermanentDeleteVisitorAPIView.as_view(), name='visitor-permanent-delete'),

]