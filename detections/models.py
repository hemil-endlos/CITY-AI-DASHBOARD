from django.db import models
from django.utils import timezone


class Detection(models.Model):
    STATUS_NEW = "new"
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]
    MODEL_CART = "cart"
    MODEL_HELMET = "helmet"
    MODEL_POTHOLE = "pothole"
    MODEL_GARBAGE = "garbage"
    MODEL_SMOKE_FIRE = "smoke_fire"
    MODEL_CHOICES = [
        (MODEL_CART, "Cart Detection"),
        (MODEL_HELMET, "Helmet Detection"),
        (MODEL_POTHOLE, "Pothole Detection"),
        (MODEL_GARBAGE, "Garbage Detection"),
        (MODEL_SMOKE_FIRE, "Smoke/Fire Detection"),
    ]

    name = models.CharField(max_length=100, unique=True)
    model_type = models.CharField(max_length=50, choices=MODEL_CHOICES, default=MODEL_CART)
    violation_type = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(upload_to="detections/", null=True, blank=True)
    plate_number = models.CharField(max_length=20, null=True, blank=True)
    plate_confidence = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    detected_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-detected_at", "-id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

