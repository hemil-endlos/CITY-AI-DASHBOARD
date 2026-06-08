import hmac
import logging

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class _APIKeyUser:
    """Sentinel user object returned when M2M API key authentication succeeds."""

    is_authenticated = True
    is_active = True
    is_anonymous = False
    pk = None

    def __str__(self) -> str:
        return "detection-service"


_API_KEY_USER = _APIKeyUser()


class DetectionServiceAuthentication(BaseAuthentication):
    """
    Validates the X-API-Key request header against DETECTION_API_KEY in settings.

    - When DETECTION_API_KEY is not configured, authentication is skipped so
      dev/test environments work without any setup.
    - Uses constant-time comparison to prevent timing-based key enumeration.
    """

    def authenticate(self, request):
        api_key = getattr(settings, "DETECTION_API_KEY", "")
        if not api_key:
            return None  # Auth disabled — pass through

        provided = request.META.get("HTTP_X_API_KEY", "")
        if not provided:
            return None  # No key supplied — let other auth classes handle it

        if not hmac.compare_digest(provided.encode(), api_key.encode()):
            logger.warning(
                "api_key_rejected | remote_addr=%s",
                request.META.get("REMOTE_ADDR", "unknown"),
            )
            raise AuthenticationFailed("Invalid or missing X-API-Key header.")

        return (_API_KEY_USER, None)

    def authenticate_header(self, request):
        return "X-API-Key"
