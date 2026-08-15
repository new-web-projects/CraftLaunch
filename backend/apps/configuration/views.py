"""
Two kinds of read here. PublicConfigurationView is unauthenticated —
every visitor's first page load needs the site name, logo, colors and
feature flags before anything else renders, so it has to be reachable
with no auth at all, the same reasoning as apps/catalog's PackageListView
being AllowAny. Everything else is IsAdminRole: the six settings
categories (get/update) and the asset upload endpoint.

The six settings views share one shape — GET the singleton, PATCH it —
so _SingletonConfigView below carries that once instead of repeating
get_object/get/patch six times. Each subclass is just a `model` +
`serializer_class` pair.
"""

import uuid

from django.core import mail
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.bookings.storage import get_storage_backend

from . import services
from .models import (
    EmailConfiguration,
    FeatureFlags,
    PaymentConfiguration,
    SEOConfiguration,
    SiteConfiguration,
    StorageConfiguration,
    StorageProviderChoices,
)
from .serializers import (
    EmailConfigurationSerializer,
    FeatureFlagsSerializer,
    PaymentConfigurationSerializer,
    SEOConfigurationSerializer,
    SiteConfigurationSerializer,
    StorageConfigurationSerializer,
)


class PublicConfigurationView(APIView):
    """GET /api/configuration/public/ — branding, SEO defaults, and
    feature flags. No secrets live on these three models at all
    (Storage/Email/Payment do, and are never exposed here), so this
    is a plain dict assembled from three cached reads rather than a
    ModelSerializer forced across models that aren't related."""

    permission_classes = [AllowAny]

    def get(self, request):
        site = services.get_site_configuration()
        seo = services.get_seo_configuration()
        flags = services.get_feature_flags()

        return Response(
            {
                "site": {
                    "website_name": site.website_name,
                    "tagline": site.tagline,
                    "description": site.description,
                    "logo_url": site.logo_url,
                    "favicon_url": site.favicon_url,
                    "footer_logo_url": site.footer_logo_url,
                    "light_logo_url": site.light_logo_url,
                    "dark_logo_url": site.dark_logo_url,
                    "primary_color": site.primary_color,
                    "secondary_color": site.secondary_color,
                    "accent_color": site.accent_color,
                    "default_language": site.default_language,
                    "timezone": site.timezone,
                    "date_format": site.date_format,
                    "currency": site.currency,
                    "contact_email": site.contact_email,
                    "support_email": site.support_email,
                    "support_phone": site.support_phone,
                    "business_address": site.business_address,
                    "social_links": site.social_links,
                    "copyright_text": site.copyright_text,
                    "footer_text": site.footer_text,
                },
                "seo": {
                    "site_title": seo.site_title,
                    "meta_description": seo.meta_description,
                    "meta_keywords": seo.meta_keywords,
                    "canonical_url": seo.canonical_url,
                    "robots_directive": seo.robots_directive,
                    "og_title": seo.og_title,
                    "og_description": seo.og_description,
                    "twitter_site": seo.twitter_site,
                    "twitter_card_type": seo.twitter_card_type,
                    "default_share_image_url": seo.default_share_image_url,
                    "json_ld_schema": seo.json_ld_schema,
                },
                "feature_flags": {
                    "blog_enabled": flags.blog_enabled,
                    "booking_enabled": flags.booking_enabled,
                    "reviews_enabled": flags.reviews_enabled,
                    "support_enabled": flags.support_enabled,
                    "payments_enabled": flags.payments_enabled,
                    "registration_enabled": flags.registration_enabled,
                    "developer_signup_enabled": flags.developer_signup_enabled,
                    "customer_signup_enabled": flags.customer_signup_enabled,
                    "maintenance_mode": flags.maintenance_mode,
                },
            }
        )


class _SingletonConfigView(APIView):
    """GET returns the current row; PATCH partially updates it and
    returns the updated row. Not PUT: every settings form on the
    admin panel edits one category at a time, and secret fields being
    write_only means a full PUT would have to resend every secret on
    every save (see serializers.py) — PATCH semantics are the reason
    the *_is_set fields exist at all."""

    permission_classes = [IsAdminRole]
    model = None
    serializer_class = None

    def get(self, request):
        instance = self.model.load()
        return Response(self.serializer_class(instance).data)

    def patch(self, request):
        instance = self.model.load()
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SiteConfigurationView(_SingletonConfigView):
    model = SiteConfiguration
    serializer_class = SiteConfigurationSerializer


class SEOConfigurationView(_SingletonConfigView):
    model = SEOConfiguration
    serializer_class = SEOConfigurationSerializer


class StorageConfigurationView(_SingletonConfigView):
    model = StorageConfiguration
    serializer_class = StorageConfigurationSerializer


class EmailConfigurationView(_SingletonConfigView):
    model = EmailConfiguration
    serializer_class = EmailConfigurationSerializer


class PaymentConfigurationView(_SingletonConfigView):
    model = PaymentConfiguration
    serializer_class = PaymentConfigurationSerializer


class FeatureFlagsView(_SingletonConfigView):
    model = FeatureFlags
    serializer_class = FeatureFlagsSerializer


_ASSET_FIELDS = {
    "logo": ("logo_url", "logo_key"),
    "favicon": ("favicon_url", "favicon_key"),
    "footer-logo": ("footer_logo_url", "footer_logo_key"),
    "light-logo": ("light_logo_url", "light_logo_key"),
    "dark-logo": ("dark_logo_url", "dark_logo_key"),
}

_MAX_ASSET_SIZE_BYTES = 5 * 1024 * 1024  # 5MB — branding images, not booking attachments


class SiteAssetUploadView(APIView):
    """POST /api/settings/site/assets/<asset>/ — asset is one of
    _ASSET_FIELDS's keys. Reuses apps.bookings.storage's provider
    abstraction rather than a second upload implementation: a site
    logo and a booking attachment are both "a file that needs to live
    somewhere and be fetched back by URL later", and Part 3 already
    solved that generically (see storage.py's own docstring on why
    callers never import boto3/cloudinary directly)."""

    permission_classes = [IsAdminRole]

    def post(self, request, asset):
        if asset not in _ASSET_FIELDS:
            return Response(
                {"detail": f"Unknown asset '{asset}'. Expected one of: {', '.join(_ASSET_FIELDS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > _MAX_ASSET_SIZE_BYTES:
            return Response(
                {"detail": f"File too large. Maximum is {_MAX_ASSET_SIZE_BYTES // (1024 * 1024)}MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        url_field, key_field = _ASSET_FIELDS[asset]
        site = SiteConfiguration.load()
        old_key = getattr(site, key_field)

        backend = get_storage_backend()
        safe_name = upload.name.replace("/", "_").replace("\\", "_")
        storage_key = f"site-config/{asset}/{uuid.uuid4()}-{safe_name}"
        stored = backend.save(storage_key, upload, upload.content_type or "application/octet-stream")

        setattr(site, url_field, stored.url)
        setattr(site, key_field, stored.key)
        site.save(update_fields=[url_field, key_field, "updated_at"])

        # Best-effort cleanup of the file this one replaced. A delete
        # failure here (provider hiccup, key already gone) shouldn't
        # fail the upload that already succeeded — worst case is one
        # orphaned file in storage, not a broken save.
        if old_key:
            try:
                backend.delete(old_key)
            except Exception:
                pass

        return Response({"url": stored.url, "asset": asset}, status=status.HTTP_200_OK)


class TestStorageConnectionView(APIView):
    """POST /api/settings/storage/test/ — validates the *saved*
    StorageConfiguration's credentials against the provider's own API,
    not whatever's in the current unsaved form state. Save first, then
    test — same reasoning as PATCH validating the stored row rather
    than accepting ad-hoc credentials in this request's body, which
    would mean a second, parallel path for "what credentials are we
    even testing" to get out of sync with what's actually stored."""

    permission_classes = [IsAdminRole]

    def post(self, request):
        config = StorageConfiguration.load()
        success, detail = self._test(config)

        config.last_tested_at = timezone.now()
        config.last_test_success = success
        config.save(update_fields=["last_tested_at", "last_test_success", "updated_at"])

        return Response(
            {"success": success, "detail": detail},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST,
        )

    def _test(self, config: StorageConfiguration) -> tuple[bool, str]:
        provider = config.active_provider
        if provider == StorageProviderChoices.LOCAL:
            return True, "Local disk storage doesn't require a connection test."

        if provider == StorageProviderChoices.S3:
            if not (config.s3_access_key_id and config.s3_secret_access_key and config.s3_bucket_name):
                return False, "S3 access key, secret key, and bucket name are all required."
            try:
                import boto3
                from botocore.exceptions import BotoCoreError, ClientError

                client = boto3.client(
                    "s3",
                    aws_access_key_id=config.s3_access_key_id,
                    aws_secret_access_key=config.s3_secret_access_key,
                    region_name=config.s3_region or None,
                )
                client.head_bucket(Bucket=config.s3_bucket_name)
                return True, f"Connected to S3 bucket '{config.s3_bucket_name}'."
            except (ClientError, BotoCoreError) as exc:
                return False, f"S3 connection failed: {exc}"
            except Exception as exc:  # noqa: BLE001 — surface as a test failure, not a 500
                return False, f"S3 connection failed: {exc}"

        if provider == StorageProviderChoices.CLOUDINARY:
            if not (config.cloudinary_cloud_name and config.cloudinary_api_key and config.cloudinary_api_secret):
                return False, "Cloudinary cloud name, API key, and API secret are all required."
            try:
                import cloudinary
                import cloudinary.api

                cloudinary.config(
                    cloud_name=config.cloudinary_cloud_name,
                    api_key=config.cloudinary_api_key,
                    api_secret=config.cloudinary_api_secret,
                )
                cloudinary.api.ping()
                return True, f"Connected to Cloudinary account '{config.cloudinary_cloud_name}'."
            except Exception as exc:  # noqa: BLE001 — Cloudinary's SDK raises its own broad Error type
                return False, f"Cloudinary connection failed: {exc}"

        return False, f"Unknown provider '{provider}'."


class TestEmailConnectionView(APIView):
    """POST /api/settings/email/test/ — opens (and immediately closes)
    a real SMTP connection using the saved EmailConfiguration. Doesn't
    send an email by default — that would mean every credential check
    also spams an inbox — but sends one to the requesting admin if
    `send_test_email: true` is in the request body."""

    permission_classes = [IsAdminRole]

    def post(self, request):
        config = EmailConfiguration.load()

        if not config.smtp_host:
            success, detail = False, "SMTP host is required."
        else:
            success, detail = self._test_connection(config)
            if success and request.data.get("send_test_email"):
                success, detail = self._send_test_email(config, request.user)

        config.last_tested_at = timezone.now()
        config.last_test_success = success
        config.save(update_fields=["last_tested_at", "last_test_success", "updated_at"])

        return Response(
            {"success": success, "detail": detail},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST,
        )

    def _test_connection(self, config: EmailConfiguration) -> tuple[bool, str]:
        try:
            connection = mail.get_connection(
                backend="django.core.mail.backends.smtp.EmailBackend",
                host=config.smtp_host,
                port=config.smtp_port,
                username=config.smtp_username or None,
                password=config.smtp_password or None,
                use_tls=config.use_tls,
                use_ssl=config.use_ssl,
                timeout=10,
            )
            connection.open()
            connection.close()
            return True, f"Connected to {config.smtp_host}:{config.smtp_port}."
        except Exception as exc:  # noqa: BLE001 — smtplib raises many distinct exception types
            return False, f"SMTP connection failed: {exc}"

    def _send_test_email(self, config: EmailConfiguration, admin_user) -> tuple[bool, str]:
        try:
            connection = mail.get_connection(
                backend="django.core.mail.backends.smtp.EmailBackend",
                host=config.smtp_host,
                port=config.smtp_port,
                username=config.smtp_username or None,
                password=config.smtp_password or None,
                use_tls=config.use_tls,
                use_ssl=config.use_ssl,
                timeout=10,
            )
            mail.send_mail(
                subject="CraftLaunch — test email",
                message="This is a test email from the CraftLaunch admin settings panel.",
                from_email=config.sender_email or None,
                recipient_list=[admin_user.email],
                connection=connection,
            )
            return True, f"Test email sent to {admin_user.email}."
        except Exception as exc:  # noqa: BLE001
            return False, f"Sending the test email failed: {exc}"


class TestPaymentConnectionView(APIView):
    """POST /api/settings/payment/test/ — validates the saved Razorpay
    key pair against Razorpay's API. A plain authenticated GET is a
    credential check, not "implementing payments" — Part 4's spec asks
    for configuration only, and this doesn't create, capture, or
    refund anything. Uses urllib (stdlib) rather than adding the
    razorpay SDK as a new dependency for one lightweight ping."""

    permission_classes = [IsAdminRole]

    def post(self, request):
        config = PaymentConfiguration.load()
        success, detail = self._test(config)

        config.last_tested_at = timezone.now()
        config.last_test_success = success
        config.save(update_fields=["last_tested_at", "last_test_success", "updated_at"])

        return Response(
            {"success": success, "detail": detail},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST,
        )

    def _test(self, config: PaymentConfiguration) -> tuple[bool, str]:
        if not (config.razorpay_key_id and config.razorpay_key_secret):
            return False, "Razorpay key ID and key secret are both required."

        import base64
        import urllib.error
        import urllib.request

        credentials = base64.b64encode(
            f"{config.razorpay_key_id}:{config.razorpay_key_secret}".encode()
        ).decode()
        req = urllib.request.Request(
            "https://api.razorpay.com/v1/payments?count=1",
            headers={"Authorization": f"Basic {credentials}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return True, "Razorpay credentials are valid."
                return False, f"Razorpay returned HTTP {response.status}."
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return False, "Razorpay rejected these credentials (401 Unauthorized)."
            return False, f"Razorpay returned HTTP {exc.code}."
        except urllib.error.URLError as exc:
            return False, f"Could not reach Razorpay: {exc.reason}"
        except Exception as exc:  # noqa: BLE001
            return False, f"Razorpay connection failed: {exc}"
