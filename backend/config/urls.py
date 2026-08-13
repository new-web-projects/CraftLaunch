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
    # URL prefix is "settings", not "configuration", to match the
    # contract Part 1's frontend/src/config/site.ts docstring already
    # committed to (${API_URL}/api/settings/public/) — the Django app
    # itself is still named apps.configuration internally, to avoid
    # reading as the same thing as config.settings.* (this project's
    # actual Django settings package).
    path("api/settings/", include("apps.configuration.urls")),
]