"""
Production settings.

Every value that matters for security is required from the environment
with no fallback — a missing variable should crash the app at startup,
not silently run insecurely.

Run with: DJANGO_SETTINGS_MODULE=config.settings.production
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, MIDDLEWARE, env

SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

DATABASES = {
    "default": env.db("DATABASE_URL"),
}
# Neon's pooled (PgBouncer) connection string is recommended here for
# serverless/many-worker deployments. PgBouncer's transaction pooling
# mode does not support Django's persistent connections, so keep this
# at 0 unless connecting directly to Neon (non-pooled).
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=0)
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = env.bool(
    "DB_DISABLE_SERVER_SIDE_CURSORS", default=True
)

CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS")

# ---------------------------------------------------------------------------
# Static files — WhiteNoise serves compressed, hashed assets directly from
# the app process so production doesn't need a separate static file host.
# ---------------------------------------------------------------------------

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MIDDLEWARE = MIDDLEWARE  # inherited as-is from base (WhiteNoise already included)

# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env.bool("DJANGO_HSTS_PRELOAD", default=False)

# Set when running behind a reverse proxy (nginx, the deployment/ config
# in this repo) that terminates TLS and forwards this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
