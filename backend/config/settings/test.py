"""
Settings for running the automated test suite (and CI).

Not one of the environments the spec asked for by name, but included
so "Build Verification" is a real, repeatable command rather than a
one-off manual check: fast, hermetic, and independent of whatever
Neon credentials happen to be in the developer's .env.

Run with: DJANGO_SETTINGS_MODULE=config.settings.test
"""

from .base import *  # noqa: F401,F403
from .base import env

SECRET_KEY = "django-insecure-test-only-6f2b8f"
CONFIGURATION_ENCRYPTION_KEY = "IB4tqu98secYaHy1TVCXhBn_yc-lTM_a1Vv0nGGqx9U="  # fixed, test-only
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# In-memory SQLite: fast, zero setup, no Neon credentials required.
# CI additionally runs the suite against a real Postgres service
# container (see deployment/../.github/workflows/ci.yml) before merge,
# so engine-specific behavior still gets caught before it ships.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY

AUTH_COOKIE_SECURE = False

# Captures sent mail in django.core.mail.outbox for assertions instead
# of printing or actually sending anything.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Throttling is real infrastructure worth testing, but LocMemCache
# persists for the whole test run — without this override, unrelated
# tests further down the suite start failing with 429s once earlier
# tests have used up the "5/min" login budget. A None rate is
# SimpleRateThrottle's own documented way to disable a scope entirely
# (view-level `throttle_classes` like LoginView's override
# DEFAULT_THROTTLE_CLASSES, so clearing that alone isn't enough — the
# rate itself has to go). See tests/test_throttling.py for a dedicated
# test that overrides these back on and clears the cache explicitly.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon": None, "user": None, "login": None, "password_reset": None},
}