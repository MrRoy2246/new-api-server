from django.urls import path
from .views import VisitorTrackingAPIView,LoginApiView,CameraListAPIView,VisitorListCreateAPIView, VisitorDetailAPIView,VisitorReportAPIView,UntrackVisitorListAPIView,UntrackVisitorDetailAPIView,RestoreVisitorAPIView

urlpatterns = [
    path('gateway/', VisitorTrackingAPIView.as_view(),name='visitor_tracking'),
    path('api/login/', LoginApiView.as_view()),
    path('api/cameras/', CameraListAPIView.as_view()),
    path('api/visitor/', VisitorListCreateAPIView.as_view(), name='visitor-list-create'),
    path('api/visitor/<int:pk>/', VisitorDetailAPIView.as_view(), name='visitor-detail'),
    path('api/visitor/report/', VisitorReportAPIView.as_view(), name='visitor-report'),
    path('api/visitor/untrack/', UntrackVisitorListAPIView.as_view(), name='delet-visitor-list'),
    path('api/visitor/untrack/<int:pk>/', UntrackVisitorDetailAPIView.as_view(), name='delete-visitor-report'),
    path('api/visitor/restore/<int:pk>/', RestoreVisitorAPIView.as_view(), name='restore-visitor'),
]