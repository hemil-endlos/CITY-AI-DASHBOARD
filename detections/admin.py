from django.contrib import admin

from .models import Detection


@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "model_type", "violation_type", "detected_at", "status", "created_at")
    list_filter = ("model_type", "status", "detected_at", "created_at")
    search_fields = ("name",)

