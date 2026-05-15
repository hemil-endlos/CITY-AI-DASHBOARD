import os
 
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.utils import timezone
 
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
 
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
 
from .models import Detection
from .serializers import DetectionSerializer, DetectionStatusSerializer
 
 
def dashboard(request):
    detections = Detection.objects.all()[:100]
    return render(request, "dashboard.html", {"detections": detections})
 
 
def _broadcast_detection(detection: Detection):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    data = DetectionSerializer(detection).data
    async_to_sync(channel_layer.group_send)(
        "detections",
        {"type": "detection_event", "data": {"type": "updated", "detection": data}},
    )
 
 
def _delete_image_file(image_field):
    """Safely delete image file from disk."""
    if not image_field:
        return
    try:
        path = os.path.join(settings.MEDIA_ROOT, image_field.name)
        if os.path.exists(path):
            os.remove(path)
            print(f"[Django] 🗑  Deleted old image: {image_field.name}")
    except Exception as e:
        print(f"[Django] ⚠️  Could not delete image: {e}")
 
 
@api_view(["GET", "POST"])
def detection_list_create(request):
    if request.method == "GET":
        detections = Detection.objects.all()[:200]
        serializer = DetectionSerializer(detections, many=True)
        return Response(serializer.data)
 
    # ── POST ──────────────────────────────────────────────────────────────────
    image_file = request.FILES.get("image")
    replace_id = request.data.get("replace_id")  # int or None
    model_type = request.data.get("model_type", Detection.MODEL_CART)
    violation_type = request.data.get("violation_type")
 
    if not image_file:
        return Response({"error": "Image is required"}, status=400)
 
    detected_at = timezone.now()
    timestamp_str = detected_at.strftime("%Y%m%d-%H%M%S-%f")
 
    # ── UPDATE existing record (better frame arrived) ─────────────────────────
    if replace_id:
        try:
            detection = Detection.objects.get(pk=int(replace_id))
 
            # Delete old image file from disk before replacing
            _delete_image_file(detection.image)
 
            # Save new image
            detection.image = image_file
            detection.detected_at = detected_at
            detection.model_type = model_type
            detection.violation_type = violation_type
            detection.save(update_fields=["image", "detected_at", "model_type", "violation_type"])
 
            print(f"[Django] ⬆️  Updated detection id={detection.pk} with better image")
            _broadcast_detection(detection)
            return Response(DetectionSerializer(detection).data, status=200)
 
        except Detection.DoesNotExist:
            print(f"[Django] ⚠️  replace_id={replace_id} not found, creating new record instead")
 
    # ── CREATE new record ─────────────────────────────────────────────────────
    detection = Detection.objects.create(
        name=f"{model_type.upper()}-{timestamp_str}",
        model_type=model_type,
        violation_type=violation_type,
        image=image_file,
        detected_at=detected_at,
        status=Detection.STATUS_PENDING,
    )
 
    print(f"[Django] ✅ Created detection id={detection.pk}")
    _broadcast_detection(detection)
    return Response(DetectionSerializer(detection).data, status=201)
 
 
@api_view(["POST"])
def detection_status_update(request, pk: int):
    detection = get_object_or_404(Detection, pk=pk)
    serializer = DetectionStatusSerializer(detection, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        _broadcast_detection(detection)
        return Response(DetectionSerializer(detection).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
 
@require_http_methods(["POST"])
def approve_detection(request, pk: int):
    detection = get_object_or_404(Detection, pk=pk)
    detection.status = Detection.STATUS_APPROVED
    detection.save(update_fields=["status"])
    _broadcast_detection(detection)
    return dashboard(request)
 
 
@require_http_methods(["POST"])
def reject_detection(request, pk: int):
    detection = get_object_or_404(Detection, pk=pk)
    detection.status = Detection.STATUS_REJECTED
    detection.save(update_fields=["status"])
    _broadcast_detection(detection)
    return dashboard(request)