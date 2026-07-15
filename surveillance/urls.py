import re

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as serve_static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("detections.urls")),
]

# Always serve media locally so uploaded images are visible regardless of DEBUG.
# django.conf.urls.static.static() is a no-op when DEBUG=False, so MEDIA_URL is
# routed directly through django.views.static.serve instead.
urlpatterns += [
    re_path(
        r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")),
        serve_static,
        {"document_root": settings.MEDIA_ROOT},
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)