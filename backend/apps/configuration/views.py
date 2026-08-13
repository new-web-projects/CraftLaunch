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
    """POST /api/configuration/site/assets/<asset>/ — asset is one of
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