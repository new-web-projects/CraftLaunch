"""
Every secret field (SMTP password, storage/payment API secrets) is
write_only here — a GET from an admin settings page never echoes the
real value back, only a `<field>_is_set` boolean the frontend can show
as "configured" / "not set" without ever holding the plaintext
client-side. This is a second, independent layer on top of
EncryptedTextField's at-rest encryption (fields.py): that one protects
a database dump, this one protects the browser network tab, React
DevTools state, and server logs of API responses. An admin who wants
to change a secret sends a new value; an admin who wants to leave it
alone sends nothing (PATCH, not PUT — see views.py) and the stored
value is untouched.
"""

from rest_framework import serializers

from .models import (
    EmailConfiguration,
    FeatureFlags,
    PaymentConfiguration,
    SEOConfiguration,
    SiteConfiguration,
    StorageConfiguration,
)


class SiteConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfiguration
        fields = [
            "website_name",
            "tagline",
            "description",
            "logo_url",
            "favicon_url",
            "footer_logo_url",
            "light_logo_url",
            "dark_logo_url",
            "primary_color",
            "secondary_color",
            "accent_color",
            "default_language",
            "timezone",
            "date_format",
            "currency",
            "contact_email",
            "support_email",
            "support_phone",
            "business_address",
            "social_links",
            "copyright_text",
            "footer_text",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
        # *_key fields (logo_key, favicon_key, ...) are deliberately
        # excluded: they're an internal implementation detail for
        # cleaning up the old file on re-upload (see services.py),
        # not something an admin form needs to see or edit directly.
        # Logo/favicon/footer_logo *_url fields are also read-only
        # here — they're only ever set via the dedicated upload
        # endpoint (SiteAssetUploadView), never by hand-typing a URL
        # into the general settings form.


class SEOConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SEOConfiguration
        fields = [
            "site_title",
            "meta_description",
            "meta_keywords",
            "canonical_url",
            "robots_directive",
            "google_verification",
            "bing_verification",
            "og_title",
            "og_description",
            "facebook_domain_verification",
            "twitter_site",
            "twitter_card_type",
            "default_share_image_url",
            "json_ld_schema",
            "updated_at",
        ]
        read_only_fields = ["updated_at", "default_share_image_url"]


class StorageConfigurationSerializer(serializers.ModelSerializer):
    s3_secret_access_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    cloudinary_api_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    s3_secret_access_key_is_set = serializers.SerializerMethodField()
    cloudinary_api_secret_is_set = serializers.SerializerMethodField()

    class Meta:
        model = StorageConfiguration
        fields = [
            "active_provider",
            "s3_enabled",
            "cloudinary_enabled",
            "s3_access_key_id",
            "s3_secret_access_key",
            "s3_secret_access_key_is_set",
            "s3_bucket_name",
            "s3_region",
            "cloudinary_cloud_name",
            "cloudinary_api_key",
            "cloudinary_api_secret",
            "cloudinary_api_secret_is_set",
            "last_tested_at",
            "last_test_success",
            "updated_at",
        ]
        read_only_fields = ["last_tested_at", "last_test_success", "updated_at"]

    def get_s3_secret_access_key_is_set(self, obj):
        return bool(obj.s3_secret_access_key)

    def get_cloudinary_api_secret_is_set(self, obj):
        return bool(obj.cloudinary_api_secret)

    def update(self, instance, validated_data):
        # A blank submitted value means "leave the existing secret
        # alone", not "clear it" — an admin re-saving the S3 bucket
        # name shouldn't have to also re-paste the secret key every
        # time just because the form field renders empty (write_only
        # fields never come back from GET, so the form can't
        # pre-fill them).
        for secret_field in ("s3_secret_access_key", "cloudinary_api_secret"):
            if secret_field in validated_data and not validated_data[secret_field]:
                validated_data.pop(secret_field)
        return super().update(instance, validated_data)


class EmailConfigurationSerializer(serializers.ModelSerializer):
    smtp_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    smtp_password_is_set = serializers.SerializerMethodField()

    class Meta:
        model = EmailConfiguration
        fields = [
            "smtp_host",
            "smtp_port",
            "smtp_username",
            "smtp_password",
            "smtp_password_is_set",
            "sender_name",
            "sender_email",
            "reply_email",
            "use_tls",
            "use_ssl",
            "last_tested_at",
            "last_test_success",
            "updated_at",
        ]
        read_only_fields = ["last_tested_at", "last_test_success", "updated_at"]

    def get_smtp_password_is_set(self, obj):
        return bool(obj.smtp_password)

    def update(self, instance, validated_data):
        if "smtp_password" in validated_data and not validated_data["smtp_password"]:
            validated_data.pop("smtp_password")
        return super().update(instance, validated_data)


class PaymentConfigurationSerializer(serializers.ModelSerializer):
    razorpay_key_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    razorpay_webhook_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    razorpay_key_secret_is_set = serializers.SerializerMethodField()
    razorpay_webhook_secret_is_set = serializers.SerializerMethodField()

    class Meta:
        model = PaymentConfiguration
        fields = [
            "razorpay_key_id",
            "razorpay_key_secret",
            "razorpay_key_secret_is_set",
            "razorpay_webhook_secret",
            "razorpay_webhook_secret_is_set",
            "default_currency",
            "mode",
            "is_enabled",
            "last_tested_at",
            "last_test_success",
            "updated_at",
        ]
        read_only_fields = ["last_tested_at", "last_test_success", "updated_at"]

    def get_razorpay_key_secret_is_set(self, obj):
        return bool(obj.razorpay_key_secret)

    def get_razorpay_webhook_secret_is_set(self, obj):
        return bool(obj.razorpay_webhook_secret)

    def update(self, instance, validated_data):
        for secret_field in ("razorpay_key_secret", "razorpay_webhook_secret"):
            if secret_field in validated_data and not validated_data[secret_field]:
                validated_data.pop(secret_field)
        return super().update(instance, validated_data)


class FeatureFlagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlags
        fields = [
            "blog_enabled",
            "booking_enabled",
            "reviews_enabled",
            "support_enabled",
            "payments_enabled",
            "registration_enabled",
            "developer_signup_enabled",
            "customer_signup_enabled",
            "maintenance_mode",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]