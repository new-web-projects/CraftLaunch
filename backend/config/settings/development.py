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
