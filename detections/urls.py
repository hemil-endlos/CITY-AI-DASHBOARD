from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # REST API
    path("api/detections/", views.detection_list_create, name="detection-list-create"),
    path(
        "api/detections/<int:pk>/status/",
        views.detection_status_update,
        name="detection-status-update",
    ),
    # Simple form actions (non-AJAX fallback)
    path("detections/<int:pk>/approve/", views.approve_detection, name="approve-detection"),
    path("detections/<int:pk>/reject/", views.reject_detection, name="reject-detection"),
]

