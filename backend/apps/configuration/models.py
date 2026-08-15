"""
Part 4 — database-backed site configuration. Each model here is a
SingletonModel (apps/core/models.py): exactly one row, always pk=1.

These replace the env-configured settings that Parts 1-3 used as
interim placeholders — SITE_NAME (config/settings/base.py) and
STORAGE_PROVIDER (apps/bookings/storage.py) both call out in their own
comments that this model was coming. Neither of those env vars is
removed here: they still seed the initial row's defaults (see the
migration's data migration step) and remain the fallback for
management commands and any code path that runs before the database
is reachable, but everything that renders to a user now reads through
apps.configuration.services instead of settings.SITE_NAME directly —
see that file, and the update to apps/accounts/emails.py.

Field-level encryption (EncryptedTextField, fields.py) is used for
anything that authenticates the app to a third party if leaked: SMTP
password, storage API secrets, Razorpay key secret and webhook
secret. Non-secret credentials that are meant to be semi-public (S3
bucket/region, Razorpay key_id — the half of a Razorpay key pair
that's safe client-side) stay as plain CharFields.
"""

from django.db import models

from apps.core.models import SingletonModel, TimeStampedModel

from .fields import EncryptedTextField


class SiteConfiguration(SingletonModel, TimeStampedModel):
    """Website identity, branding, and contact/locale defaults —
    the fields every page on the public site potentially reads."""

    # Identity
    website_name = models.CharField(max_length=100, default="CraftLaunch")
    tagline = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")

    # Branding — logo/favicon/footer_logo/light/dark variants. Each
    # pair (url + key) mirrors ProjectAttachment's pattern of
    # recording where a file actually lives (bookings/models.py), but
    # simplified: a singleton config only ever has one *current*
    # value per slot, not a history, so there's no need for a
    # separate provider-tracking table. `_key` is kept alongside
    # `_url` purely so a re-upload can delete the previous file from
    # storage instead of orphaning it — see services.py.
    logo_url = models.CharField(max_length=500, blank=True, default="")
    logo_key = models.CharField(max_length=500, blank=True, default="")
    favicon_url = models.CharField(max_length=500, blank=True, default="")
    favicon_key = models.CharField(max_length=500, blank=True, default="")
    footer_logo_url = models.CharField(max_length=500, blank=True, default="")
    footer_logo_key = models.CharField(max_length=500, blank=True, default="")
    light_logo_url = models.CharField(max_length=500, blank=True, default="")
    light_logo_key = models.CharField(max_length=500, blank=True, default="")
    dark_logo_url = models.CharField(max_length=500, blank=True, default="")
    dark_logo_key = models.CharField(max_length=500, blank=True, default="")

    # Theme — hex, not the OKLCH values globals.css actually uses:
    # admin-facing color pickers speak hex, and converting hex to the
    # CSS custom properties at render time is a frontend-phase concern
    # (docs/ARCHITECTURE.md will get an entry once that lands). Until
    # an admin changes these, the site keeps looking exactly like it
    # does today — these defaults are cosmetic-only placeholders, not
    # a re-theme.
    primary_color = models.CharField(max_length=7, default="#D97706")
    secondary_color = models.CharField(max_length=7, default="#78716C")
    accent_color = models.CharField(max_length=7, default="#F59E0B")

    # Locale/regional defaults
    default_language = models.CharField(max_length=10, default="en")
    timezone = models.CharField(max_length=64, default="UTC")
    date_format = models.CharField(max_length=20, default="DD/MM/YYYY")
    currency = models.CharField(max_length=3, default="INR")

    # Contact
    contact_email = models.EmailField(blank=True, default="")
    support_email = models.EmailField(blank=True, default="")
    support_phone = models.CharField(max_length=30, blank=True, default="")
    business_address = models.TextField(blank=True, default="")

    # Social links — {"twitter": "https://...", "github": "https://...", ...}.
    # A JSON map instead of one field per platform: the set of
    # platforms an admin wants to link is inherently open-ended, and a
    # fixed field list would mean a migration every time a new one
    # comes up.
    social_links = models.JSONField(default=dict, blank=True)

    copyright_text = models.CharField(max_length=255, blank=True, default="")
    footer_text = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Site Configuration"

    def __str__(self):
        return self.website_name


class SEOConfiguration(SingletonModel, TimeStampedModel):
    """Default meta tags. Per-page overrides (a package or blog post
    setting its own title/description) are a later part — these are
    the site-wide fallback every page starts from."""

    site_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.CharField(max_length=500, blank=True, default="")
    meta_keywords = models.CharField(max_length=500, blank=True, default="")
    canonical_url = models.URLField(blank=True, default="")
    robots_directive = models.CharField(max_length=100, default="index, follow")

    google_verification = models.CharField(max_length=255, blank=True, default="")
    bing_verification = models.CharField(max_length=255, blank=True, default="")

    # Open Graph
    og_title = models.CharField(max_length=255, blank=True, default="")
    og_description = models.CharField(max_length=500, blank=True, default="")
    facebook_domain_verification = models.CharField(max_length=255, blank=True, default="")

    # Twitter/X card
    twitter_site = models.CharField(max_length=100, blank=True, default="")
    twitter_card_type = models.CharField(max_length=30, default="summary_large_image")

    default_share_image_url = models.CharField(max_length=500, blank=True, default="")
    default_share_image_key = models.CharField(max_length=500, blank=True, default="")

    # Structured data (schema.org Organization/WebSite, typically) —
    # a JSON map kept as free-form rather than modeled field-by-field,
    # since JSON-LD schemas vary by type and this only needs to be
    # valid JSON emitted verbatim into a <script type="application/ld+json">
    # tag, not queried or validated field-by-field.
    json_ld_schema = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "SEO Configuration"

    def __str__(self):
        return "SEO Configuration"


class StorageProviderChoices(models.TextChoices):
    """Mirrors the provider names apps/bookings/storage.py's
    get_storage_backend() dispatches on exactly — these are not
    independent lists to keep in sync by hand, this one *is* the
    source of truth: that function reads StorageConfiguration.active_provider
    (this model) directly, see that file's module docstring."""

    LOCAL = "LOCAL", "Local disk"
    S3 = "S3", "Amazon S3"
    CLOUDINARY = "CLOUDINARY", "Cloudinary"


class StorageConfiguration(SingletonModel, TimeStampedModel):
    """Which storage provider is active, and the credentials for each
    one a provider might be switched to. Enabling a provider and
    making it *active* are deliberately separate: an admin can save
    and validate S3 credentials before cutting over, rather than the
    switch itself being the first time those credentials get used."""

    active_provider = models.CharField(
        max_length=20, choices=StorageProviderChoices.choices, default=StorageProviderChoices.LOCAL
    )
    s3_enabled = models.BooleanField(default=False)
    cloudinary_enabled = models.BooleanField(default=False)

    s3_access_key_id = models.CharField(max_length=255, blank=True, default="")
    s3_secret_access_key = EncryptedTextField(blank=True, default="")
    s3_bucket_name = models.CharField(max_length=255, blank=True, default="")
    s3_region = models.CharField(max_length=50, blank=True, default="")

    cloudinary_cloud_name = models.CharField(max_length=255, blank=True, default="")
    cloudinary_api_key = models.CharField(max_length=255, blank=True, default="")
    cloudinary_api_secret = EncryptedTextField(blank=True, default="")

    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_success = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "Storage Configuration"

    def __str__(self):
        return f"Storage Configuration ({self.active_provider})"


class EmailConfiguration(SingletonModel, TimeStampedModel):
    """SMTP delivery settings. Falls back to config/settings/base.py's
    env-configured EMAIL_* values (see services.py) until an admin
    explicitly saves a configuration here — same interim pattern as
    SiteConfiguration.website_name and SITE_NAME."""

    smtp_host = models.CharField(max_length=255, blank=True, default="")
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True, default="")
    smtp_password = EncryptedTextField(blank=True, default="")

    sender_name = models.CharField(max_length=255, blank=True, default="")
    sender_email = models.EmailField(blank=True, default="")
    reply_email = models.EmailField(blank=True, default="")

    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)

    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_success = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "Email Configuration"

    def __str__(self):
        return "Email Configuration"


class PaymentConfiguration(SingletonModel, TimeStampedModel):
    """Razorpay credentials and mode. Configuration only, per Part 4's
    spec — no payment-taking code reads this yet. is_enabled defaults
    to False on purpose: saving credentials here should never be what
    silently turns payments on for the live site."""

    class Mode(models.TextChoices):
        SANDBOX = "SANDBOX", "Sandbox"
        LIVE = "LIVE", "Live"

    razorpay_key_id = models.CharField(max_length=255, blank=True, default="")
    razorpay_key_secret = EncryptedTextField(blank=True, default="")
    razorpay_webhook_secret = EncryptedTextField(blank=True, default="")
    default_currency = models.CharField(max_length=3, default="INR")
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.SANDBOX)
    is_enabled = models.BooleanField(default=False)

    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_success = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "Payment Configuration"

    def __str__(self):
        return f"Payment Configuration ({self.mode})"


class FeatureFlags(SingletonModel, TimeStampedModel):
    """Coarse, site-wide on/off switches. Per-user or percentage
    rollout flags are a different (and heavier) feature than what
    Part 4 asked for — this is deliberately just booleans an admin
    flips, read the same way on every request via services.py."""

    blog_enabled = models.BooleanField(default=True)
    booking_enabled = models.BooleanField(default=True)
    reviews_enabled = models.BooleanField(default=True)
    support_enabled = models.BooleanField(default=True)
    payments_enabled = models.BooleanField(default=False)
    registration_enabled = models.BooleanField(default=True)
    developer_signup_enabled = models.BooleanField(default=True)
    customer_signup_enabled = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Feature Flags"
        verbose_name_plural = "Feature Flags"

    def __str__(self):
        return "Feature Flags"