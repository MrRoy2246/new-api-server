from django.urls import path
# from .views import VisitorTrackingAPIView,LoginApiView,CameraListAPIView,VisitorAPIView,RestoreVisitorAPIView



# # VisitorListCreateAPIView, VisitorDetailAPIView,VisitorActiveAPIView,SoftDeleteVisitorListAPIView,SoftDeleteVisitorDetailAPIView,TrackedVisitorDetailAPIView,TrackedVisitorAPIView,UntrackedVisitorAPIView,UntrackedVisitorDetailAPIView,PermanentDeleteVisitorAPIView,VisitorTrackAPIView


from .views import VisitorAPIView, RestoreVisitorAPIView,MLDetectionAPIView,VisitorDetectionsView,VisitorReportAPIView,MockMLServerView,ToggleTrackingAPIView,CameraUpdateView,VisitorLastLocationAPIView,VisitorEventDeleteAPIView

urlpatterns = [
    # path('gateway/', VisitorTrackingAPIView.as_view(),name='visitor_tracking'),
    # path('api/login/', LoginApiView.as_view()),
    # path('api/cameras/', CameraListAPIView.as_view()),
    # path('api/visitor/', VisitorListCreateAPIView.as_view(), name='visitor-list-create'),
    # path('api/visitor/<int:pk>/', VisitorDetailAPIView.as_view(), name='visitor-detail'),
    # path('api/visitor/track/', TrackedVisitorAPIView.as_view(), name='track-visitor-list'),
    # path('api/visitor/track/<int:pk>/', TrackedVisitorDetailAPIView.as_view(), name='track-visitor-detail'),
    # path('api/visitor/untrack/', UntrackedVisitorAPIView.as_view(), name='untrack-visitor-list'),
    # path('api/visitor/untrack/<int:pk>/', UntrackedVisitorDetailAPIView.as_view(), name='untrack-visitor-detail'),
    # path('api/visitor/active/', VisitorActiveAPIView.as_view(), name='visitor-report'),
    # path('api/visitor/soft/', SoftDeleteVisitorListAPIView.as_view(), name='soft-visitor-list'),
    # path('api/visitor/soft/<int:pk>/', SoftDeleteVisitorDetailAPIView.as_view(), name='soft-visitor-report'),
    # path('api/visitor/restore/<int:pk>/', RestoreVisitorAPIView.as_view(), name='restore-visitor'),
    # path('api/visitor/delete/<int:pk>/', PermanentDeleteVisitorAPIView.as_view(), name='visitor-permanent-delete'),
    # path('api/visitor/getins/',VisitorTrackAPIView.as_view(),name='visitorgetinstitute')
    path('visitor/', VisitorAPIView.as_view()),              # List, Create
    path('visitor/<str:pk>/', VisitorAPIView.as_view()),     # Detail, Update, Delete
    path('visitor/restore/<str:pk>/', RestoreVisitorAPIView.as_view()),  # Restore
    # path('api/visitor/types/', VisitorTypeAPIView.as_view(), name='visitor-types'),
    path('ml-detect/', MLDetectionAPIView.as_view(), name='ml_detect'),
    path('visitor/detections/<str:visitor_id>/', VisitorDetectionsView.as_view(), name='visitor-detections'),
    # path('visitor/report/', VisitorReportAPIView.as_view(), name='visitor-report'),

    path('api/visitor-reports/', VisitorReportAPIView.as_view(), name='visitor-reports'),
    path('mock-ml/', MockMLServerView.as_view(), name='mock_ml_server'),

    path('visitors/toggle-tracking/<str:pk>/', ToggleTrackingAPIView.as_view(), name='toggle-tracking'),
    path('fetch_camera/', CameraUpdateView.as_view(), name='fetch_camera'),
    path('visitors/last-location/<str:pk>/', VisitorLastLocationAPIView.as_view(), name='visitor-last-location'),
    path("events/delete/<str:pk>/", VisitorEventDeleteAPIView.as_view(), name="delete-event"),


    

]