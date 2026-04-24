"""
CREDA URL configuration.
"""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include

def _no_content(*args, **kwargs):
    return HttpResponse(status=204)

urlpatterns = [
    # Chrome requests this when devtools is open; silence 404s in runserver logs
    path(
        ".well-known/appspecific/com.chrome.devtools.json",
        _no_content,
        name="chrome_devtools_json",
    ),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("accounts.urls")),
    path("", include("dashboard.urls")),
]
