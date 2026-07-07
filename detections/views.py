import io
import logging

from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from PIL import Image as PillowImage
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .authentication import DetectionServiceAuthentication
from .models import Detection
from .serializers import DetectionSerializer, DetectionStatusSerializer

logger = logging.getLogger(__name__)

# Allowed image MIME types based on Pillow format identifiers
_ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def dashboard(request):
    detections = Detection.objects.all()[:100]
    return render(request, "dashboard.html", {"detections": detections})


def _broadcast_detection(detection: Detection) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    data = DetectionSerializer(detection).data
    async_to_sync(channel_layer.group_send)(
        "detections",
        {"type": "detection_event", "data": {"type": "updated", "detection": data}},
    )


def _delete_image_file(image_field) -> None:
    """Delete an image file from disk, logging any failure."""
    if not image_field or not image_field.name:
        return
    try:
        image_field.storage.delete(image_field.name)
        logger.debug("image_deleted | path=%s", image_field.name)
    except OSError as exc:
        logger.warning("image_delete_failed | path=%s error=%s", image_field.name, exc)


def _delete_image_by_name(name: str) -> None:
    """Delete an image file by storage-relative name, logging any failure."""
    if not name:
        return
    try:
        from django.core.files.storage import default_storage
        default_storage.delete(name)
        logger.debug("image_deleted | path=%s", name)
    except OSError as exc:
        logger.warning("image_delete_failed | path=%s error=%s", name, exc)


def _validate_image_file(file) -> str | None:
    """
    Validate uploaded image using Pillow. Returns an error message string on
    failure, or None if the image is valid.
    """
    max_bytes = getattr(settings, "MAX_UPLOAD_IMAGE_BYTES", 10 * 1024 * 1024)
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    if size > max_bytes:
        return f"Image too large: {size} bytes (max {max_bytes})."
    if size == 0:
        return "Uploaded file is empty."

    try:
        img = PillowImage.open(io.BytesIO(file.read()))
        img.verify()
        file.seek(0)
        if img.format not in _ALLOWED_IMAGE_FORMATS:
            return f"Unsupported image format: {img.format}. Allowed: JPEG, PNG, WEBP."
    except Exception as exc:
        file.seek(0)
        return f"Invalid image file: {exc}"

    return None


@api_view(["GET", "POST"])
@authentication_classes([DetectionServiceAuthentication])
@permission_classes([AllowAny])
def detection_list_create(request):
    if request.method == "GET":
        queryset = Detection.objects.all()
        page = request.query_params.get("page")
        if page is not None:
            from rest_framework.pagination import PageNumberPagination
            paginator = PageNumberPagination()
            paginator.page_size = int(request.query_params.get("page_size", 50))
            result = paginator.paginate_queryset(queryset, request)
            serializer = DetectionSerializer(result, many=True)
            return paginator.get_paginated_response(serializer.data)
        # Non-paginated fallback — cap at 200 to protect the DB
        detections = queryset[:200]
        serializer = DetectionSerializer(detections, many=True)
        return Response(serializer.data)

    # ── POST ──────────────────────────────────────────────────────────────────
    # Enforce API key for ingest writes
    api_key = getattr(settings, "DETECTION_API_KEY", "")
    if api_key and not isinstance(request.user, type(None)):
        from .authentication import _API_KEY_USER
        if request.user is not _API_KEY_USER and not getattr(request.user, "is_authenticated", False):
            return Response({"error": "Authentication required."}, status=status.HTTP_403_FORBIDDEN)

    image_file = request.FILES.get("image")
    replace_id = request.data.get("replace_id")
    model_type = request.data.get("model_type", Detection.MODEL_CART)
    violation_type = request.data.get("violation_type")
    latitude = None
    longitude = None
    try:
        _lat = request.data.get("latitude")
        if _lat is not None:
            latitude = float(_lat)
    except (TypeError, ValueError):
        pass
    try:
        _lng = request.data.get("longitude")
        if _lng is not None:
            longitude = float(_lng)
    except (TypeError, ValueError):
        pass

    if not image_file:
        return Response({"error": "Image is required."}, status=status.HTTP_400_BAD_REQUEST)

    validation_error = _validate_image_file(image_file)
    if validation_error:
        logger.warning("image_validation_failed | error=%s", validation_error)
        return Response({"error": validation_error}, status=status.HTTP_400_BAD_REQUEST)

    detected_at = timezone.now()
    timestamp_str = detected_at.strftime("%Y%m%d-%H%M%S-%f")

    # ── UPDATE existing record (better frame arrived) ─────────────────────────
    if replace_id:
        try:
            detection = Detection.objects.get(pk=int(replace_id))
            # Capture old image name before overwriting
            old_image_name = detection.image.name if detection.image else None

            detection.image = image_file
            detection.detected_at = detected_at
            detection.model_type = model_type
            detection.violation_type = violation_type
            if latitude is not None:
                detection.latitude = latitude
            if longitude is not None:
                detection.longitude = longitude
            update_fields = ["image", "detected_at", "model_type", "violation_type", "latitude", "longitude"]
            detection.save(update_fields=update_fields)

            # Delete old image only after the DB write succeeds
            if old_image_name:
                _delete_image_by_name(old_image_name)

            logger.info("detection_updated | id=%s model=%s", detection.pk, model_type)
            _broadcast_detection(detection)
            return Response(DetectionSerializer(detection).data, status=status.HTTP_200_OK)

        except Detection.DoesNotExist:
            logger.warning("replace_id_not_found | replace_id=%s creating_new=true", replace_id)
        except ValueError:
            return Response({"error": "replace_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

    # ── CREATE new record ─────────────────────────────────────────────────────
    detection = Detection.objects.create(
        name=f"{model_type.upper()}-{timestamp_str}",
        model_type=model_type,
        violation_type=violation_type,
        image=image_file,
        detected_at=detected_at,
        status=Detection.STATUS_NEW,
        latitude=latitude,
        longitude=longitude,
    )

    logger.info("detection_created | id=%s model=%s", detection.pk, model_type)
    _broadcast_detection(detection)
    return Response(DetectionSerializer(detection).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@authentication_classes([DetectionServiceAuthentication])
@permission_classes([AllowAny])
def update_detection_plate(request, pk: int):
    detection = get_object_or_404(Detection, pk=pk)
    plate_number = request.data.get("plate_number")
    plate_confidence = request.data.get("plate_confidence")

    update_fields = []
    if plate_number is not None:
        detection.plate_number = str(plate_number)[:20]
        update_fields.append("plate_number")
    if plate_confidence is not None:
        try:
            detection.plate_confidence = float(plate_confidence)
            update_fields.append("plate_confidence")
        except (TypeError, ValueError):
            return Response({"error": "plate_confidence must be a number."}, status=status.HTTP_400_BAD_REQUEST)

    if not update_fields:
        return Response({"error": "No plate fields provided."}, status=status.HTTP_400_BAD_REQUEST)

    detection.save(update_fields=update_fields)
    logger.info("detection_plate_updated | id=%s plate=%s conf=%s", pk, plate_number, plate_confidence)
    _broadcast_detection(detection)
    return Response(DetectionSerializer(detection).data)


@api_view(["POST"])
def detection_status_update(request, pk: int):
    detection = get_object_or_404(Detection, pk=pk)
    serializer = DetectionStatusSerializer(detection, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        _broadcast_detection(detection)
        logger.info("detection_status_updated | id=%s status=%s", pk, request.data.get("status"))
        return Response(DetectionSerializer(detection).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@require_http_methods(["POST"])
def approve_detection(request, pk: int):
    detection = get_object_or_404(Detection, pk=pk)
    detection.status = Detection.STATUS_APPROVED
    detection.save(update_fields=["status"])
    logger.info("detection_approved | id=%s", pk)
    _broadcast_detection(detection)
    return dashboard(request)


@require_http_methods(["POST"])
def reject_detection(request, pk: int):
    detection = get_object_or_404(Detection, pk=pk)
    detection.status = Detection.STATUS_REJECTED
    detection.save(update_fields=["status"])
    logger.info("detection_rejected | id=%s", pk)
    _broadcast_detection(detection)
    return dashboard(request)
