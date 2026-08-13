"""
Local development settings.

Run with: DJANGO_SETTINGS_MODULE=config.settings.development
(manage.py already defaults to this, so `python manage.py runserver`
just works with no extra flags.)
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-do-not-use-in-production-6f2b8f",
)

# Encrypts apps.configuration's secret fields (SMTP password, storage/
# payment API secrets) at rest — see apps/configuration/fields.py.
# Unset here on purpose: that module falls back to deriving a key from
# SECRET_KEY when this is None, so a fresh dev checkout works with
# zero setup, same as everything else in this file.
CONFIGURATION_ENCRYPTION_KEY = env("CONFIGURATION_ENCRYPTION_KEY", default=None)

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Point this at a Neon Postgres connection string, e.g.:
#   postgres://user:password@ep-xxxx.neon.tech/craftlaunch?sslmode=require
# Neon's branching feature is a good fit here — branch a "dev" copy off
# the production database instead of diverging onto a different engine.
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)

SIMPLE_JWT["SIGNING_KEY"] = SIMPLE_JWT["SIGNING_KEY"] or SECRET_KEY

# Plain http locally, so cookies can't be marked Secure or the browser
# would silently refuse to store them.
AUTH_COOKIE_SECURE = False

# Prints verification/reset emails to the console instead of sending
# anything real — copy the link straight out of the runserver output.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# LocMemCache is per-process, which is fine for `runserver` (single
# process) but would under-count throttle hits across gunicorn's
# multiple workers — production requires Redis instead (see
# production.py). Set REDIS_URL here too if running dev via
# docker-compose (which does include a redis service) and you want
# rate-limit behavior to match production more closely.
CACHES = {
    "default": (
        {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": env("REDIS_URL")}
        if env("REDIS_URL", default=None)
        else {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    )
}

# Verbose SQL logging on demand: set DJANGO_LOG_SQL=True in .env.
if env.bool("DJANGO_LOG_SQL", default=False):
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"console": {"class": "logging.StreamHandler"}},
        "loggers": {
            "django.db.backends": {"handlers": ["console"], "level": "DEBUG"},
        },
    }