from rest_framework import serializers

from .models import Detection


class DetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detection
        fields = ["id", "name", "model_type", "violation_type", "image", "detected_at", "status", "created_at"]
        read_only_fields = ["id", "name", "status", "created_at"]


class DetectionStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detection
        fields = ["status"]

