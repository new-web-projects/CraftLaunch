"""
Base settings shared by every environment.

Nothing environment-specific lives here (no SECRET_KEY, no DEBUG, no
ALLOWED_HOSTS, no DATABASES) — each of development.py / production.py /
test.py imports `from .base import *` and supplies those explicitly.
That way a missing environment variable fails loudly in the environment
that needed it, instead of silently falling back to a base default.
"""

from datetime import timedelta
from pathlib import Path

import environ
from django.utils.csp import CSP

# backend/config/settings/base.py -> settings -> config -> backend (BASE_DIR)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Load backend/.env if present. Real deployments should set variables
# through the platform's own secret manager instead of shipping a file.
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
]

# apps.accounts (Part 2) was the first real app; apps.core/catalog/
# bookings (Part 3), apps.configuration (Part 4), and apps.payments
# (Part 6) follow the same registration pattern.
LOCAL_APPS: list[str] = [
    "apps.accounts",
    "apps.core",
    "apps.catalog",
    "apps.bookings",
    "apps.configuration",
    "apps.payments",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Swaps Django's built-in User for accounts.User (adds role, email
# verification, lockout tracking — see apps/accounts/models.py). Safe to
# do now because Part 1 never ran a real migration against a persistent
# database; changing this after real data exists would need a much more
# careful migration.
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.StrongPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# File uploads (resumes, project briefs, delivered work) are out of scope
# for Part 1 — no storage backend is wired up yet. MEDIA_ROOT exists so
# local/dev runs have somewhere sane to write to before the Admin-editable
# S3/Cloudinary switch (a later part) is implemented.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
# Secure by default now that authentication exists (Part 1 was AllowAny
# globally, flagged there as temporary — this is that follow-up). Every
# view that needs to be public sets `permission_classes = [AllowAny]`
# explicitly (register, login, refresh, forgot/reset-password, verify-email).

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        # Scoped/custom throttles used by specific views:
        "login": "5/min",
        "password_reset": "3/hour",
        "payment_action": "20/min",
    },
}


# ---------------------------------------------------------------------------
# JWT (SimpleJWT)
# ---------------------------------------------------------------------------
# Access tokens are returned in the response body and kept in memory by
# the frontend (never localStorage) — short-lived on purpose, since a
# blacklisted refresh token doesn't retroactively invalidate an
# already-issued access token still inside its own lifetime. The refresh
# token itself is never in a JSON response at all; see accounts/cookies.py.

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=1)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=None),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}
# If JWT_SIGNING_KEY wasn't set explicitly, each environment module falls
# back to its own SECRET_KEY (`SIMPLE_JWT["SIGNING_KEY"] = SIMPLE_JWT["SIGNING_KEY"] or SECRET_KEY`)
# right after it defines SECRET_KEY — base.py can't do that itself since
# SECRET_KEY isn't defined until then (see module docstring).

# Not read by SimpleJWT itself (it only knows REFRESH_TOKEN_LIFETIME) —
# used explicitly by accounts/jwt.py when remember_me=True.
JWT_REFRESH_TOKEN_LIFETIME_REMEMBER_ME = timedelta(days=env.int("JWT_REMEMBER_ME_LIFETIME_DAYS", default=30))


# ---------------------------------------------------------------------------
# Auth cookies
# ---------------------------------------------------------------------------

AUTH_REFRESH_COOKIE_NAME = "craftlaunch_refresh"
AUTH_SESSION_HINT_COOKIE_NAME = "craftlaunch_session"
AUTH_COOKIE_SAMESITE = "Lax"
# AUTH_COOKIE_SECURE is set per-environment (False in dev over plain
# http, True everywhere else) — see development.py / production.py.

CORS_ALLOW_CREDENTIALS = True  # the refresh cookie must survive a cross-origin request


# ---------------------------------------------------------------------------
# Content-Security-Policy
# ---------------------------------------------------------------------------
# Applied in every environment (not just production) so dev/test actually
# exercise the same policy that ships — the point of a CSP is defense in
# depth against XSS even if a malicious script gets injected somewhere;
# discovering it's too strict only in production defeats that. Scoped
# mainly for the Django admin and DRF's browsable API, since this backend
# doesn't otherwise render HTML — style-src allows 'unsafe-inline' because
# Django admin's own templates use inline styles.
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:", "https:"],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],  # belt-and-braces alongside X_FRAME_OPTIONS
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
}


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
# Explicit rather than relying on Django's implicit default (which is the
# same PBKDF2 hasher first in the list below) — matches the "explicit over
# implicit" approach used elsewhere (e.g. DEFAULT_AUTO_FIELD). Only
# settings/test.py overrides this, trading hash strength for test speed.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]


# ---------------------------------------------------------------------------
# Site identity & email
# ---------------------------------------------------------------------------

# Interim env-driven value, same pattern as frontend/src/config/site.ts —
# becomes Admin-editable once the Settings model + API exist.
SITE_NAME = env("SITE_NAME", default="CraftLaunch")

# Used to build links inside verification/reset emails.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@craftlaunch.example")
# EMAIL_BACKEND / EMAIL_HOST_* are set per-environment: console in dev,
# locmem in test, real SMTP in production.


# ---------------------------------------------------------------------------
# Storage provider (Part 3)
# ---------------------------------------------------------------------------
# Selects the backend apps/bookings/storage.get_storage_backend() returns.
# LOCAL needs nothing further. Only the credentials for whichever
# provider is actually selected need to be set — S3's and Cloudinary's
# are read here either way since get_storage_backend() only
# instantiates the class that matches STORAGE_PROVIDER.

STORAGE_PROVIDER = env("STORAGE_PROVIDER", default="LOCAL")

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default=None)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default=None)
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)

CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME", default=None)
CLOUDINARY_API_KEY = env("CLOUDINARY_API_KEY", default=None)
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET", default=None)

# Part 6 — read only to seed PaymentConfiguration's first row on
# migrate (apps/configuration/migrations/0003_seed_razorpay_from_env.py),
# the same one-time bootstrap AWS_ACCESS_KEY_ID/CLOUDINARY_CLOUD_NAME
# get above. Nothing in apps.payments reads these settings directly —
# every actual Razorpay API call goes through
# apps.payments.services.RazorpayClientFactory, which reads the
# database row (admin-editable, encrypted at rest — see
# apps/configuration/fields.py) so switching test/live mode never
# needs a redeploy.
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default=None)
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default=None)
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default=None)

# Booking attachment validation (bookings/validators.py)
BOOKING_ATTACHMENT_MAX_SIZE_MB = env.int("BOOKING_ATTACHMENT_MAX_SIZE_MB", default=25)
BOOKING_ATTACHMENT_ALLOWED_EXTENSIONS = env.list(
    "BOOKING_ATTACHMENT_ALLOWED_EXTENSIONS",
    default=[
        "jpg", "jpeg", "png", "gif", "webp", "svg",  # images
        "pdf",
        "zip",
        "doc", "docx",
        "xls", "xlsx", "csv",  # spreadsheets
        "txt",
    ],
)