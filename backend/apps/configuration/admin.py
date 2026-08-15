"""
Registered here the same way accounts/catalog/bookings are, as an
operational fallback distinct from the real admin surface — the
Next.js admin panel these models exist for. has_add_permission and
has_delete_permission are both locked down: SingletonModel already
makes the ORM refuse a second row or a delete (apps/core/models.py),
but Django's admin normally offers "Add" and "Delete" buttons before
that check would ever run — hiding them here avoids an admin clicking
"Add Storage Configuration" and getting a confusing IntegrityError-free
no-op instead of a second row.
"""

from django.contrib import admin

from .models import (
    EmailConfiguration,
    FeatureFlags,
    PaymentConfiguration,
    SEOConfiguration,
    SiteConfiguration,
    StorageConfiguration,
)


class SingletonAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(SingletonAdmin):
    list_display = ["website_name", "contact_email", "updated_at"]


@admin.register(SEOConfiguration)
class SEOConfigurationAdmin(SingletonAdmin):
    list_display = ["site_title", "updated_at"]


@admin.register(StorageConfiguration)
class StorageConfigurationAdmin(SingletonAdmin):
    list_display = ["active_provider", "s3_enabled", "cloudinary_enabled", "last_test_success", "updated_at"]
    # Secret fields are intentionally absent from list_display and are
    # shown in the detail form as widgets Django renders as normal
    # text inputs — this admin is an internal operational fallback,
    # not the hardened surface the real admin panel's masked *_is_set
    # fields provide (see serializers.py). Treat direct DB-admin
    # access to this page itself as sensitive.
    readonly_fields = ["last_tested_at", "last_test_success", "updated_at"]


@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(SingletonAdmin):
    list_display = ["smtp_host", "sender_email", "last_test_success", "updated_at"]
    readonly_fields = ["last_tested_at", "last_test_success", "updated_at"]


@admin.register(PaymentConfiguration)
class PaymentConfigurationAdmin(SingletonAdmin):
    list_display = ["mode", "is_enabled", "last_test_success", "updated_at"]
    readonly_fields = ["last_tested_at", "last_test_success", "updated_at"]


@admin.register(FeatureFlags)
class FeatureFlagsAdmin(SingletonAdmin):
    list_display = ["maintenance_mode", "booking_enabled", "payments_enabled", "updated_at"]
