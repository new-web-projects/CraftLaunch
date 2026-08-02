"""
URL configuration for the CraftLaunch API.

Part 1 only wires up the Django admin (built-in, no custom models yet)
and a health-check endpoint. Each future part adds its own
`path("api/<feature>/", include("apps.<feature>.urls"))` line here.
"""

from django.contrib import admin
from django.urls import include, path

from config.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/bookings/", include("apps.bookings.urls")),
]