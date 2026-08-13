"""
Seeds each singleton's first row from the env-configured settings it
replaces, so upgrading to Part 4 doesn't blank out credentials a
deployment already has working — the same reasoning as
SiteConfiguration.website_name defaulting to settings.SITE_NAME.
RAZORPAY_* isn't seeded: those .env.example entries were reserved
placeholders from an earlier part but were never actually wired to a
Django setting (grep the codebase — nothing reads them), so there's
nothing real to seed from yet.

getattr(...) with defaults throughout because EMAIL_HOST and friends
only exist in production.py — development.py uses the console email
backend and never defines them, and this migration has to run cleanly
under every settings module.
"""

from django.conf import settings
from django.db import migrations


def seed_from_env(apps, schema_editor):
    SiteConfiguration = apps.get_model("configuration", "SiteConfiguration")
    StorageConfiguration = apps.get_model("configuration", "StorageConfiguration")
    EmailConfiguration = apps.get_model("configuration", "EmailConfiguration")

    SiteConfiguration.objects.get_or_create(
        pk=1,
        defaults={"website_name": getattr(settings, "SITE_NAME", "CraftLaunch")},
    )

    aws_key = getattr(settings, "AWS_ACCESS_KEY_ID", None) or ""
    cloudinary_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", None) or ""
    StorageConfiguration.objects.get_or_create(
        pk=1,
        defaults={
            "active_provider": getattr(settings, "STORAGE_PROVIDER", "LOCAL"),
            "s3_enabled": bool(aws_key),
            "cloudinary_enabled": bool(cloudinary_name),
            "s3_access_key_id": aws_key,
            "s3_secret_access_key": getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or "",
            "s3_bucket_name": getattr(settings, "AWS_STORAGE_BUCKET_NAME", None) or "",
            "s3_region": getattr(settings, "AWS_S3_REGION_NAME", None) or "",
            "cloudinary_cloud_name": cloudinary_name,
            "cloudinary_api_key": getattr(settings, "CLOUDINARY_API_KEY", None) or "",
            "cloudinary_api_secret": getattr(settings, "CLOUDINARY_API_SECRET", None) or "",
        },
    )

    EmailConfiguration.objects.get_or_create(
        pk=1,
        defaults={
            "smtp_host": getattr(settings, "EMAIL_HOST", "") or "",
            "smtp_port": getattr(settings, "EMAIL_PORT", 587),
            "smtp_username": getattr(settings, "EMAIL_HOST_USER", "") or "",
            "smtp_password": getattr(settings, "EMAIL_HOST_PASSWORD", "") or "",
            "sender_email": getattr(settings, "DEFAULT_FROM_EMAIL", "") or "",
            "reply_email": getattr(settings, "DEFAULT_FROM_EMAIL", "") or "",
            "use_tls": getattr(settings, "EMAIL_USE_TLS", True),
        },
    )


def unseed(apps, schema_editor):
    # Reversing a data migration that only creates rows: delete them.
    # Not "restore blank" — DeleteModel on the way down in 0001's
    # reverse already removes the tables entirely, so this only
    # matters if someone reverses *just* this migration and stops.
    for model_name in ("SiteConfiguration", "StorageConfiguration", "EmailConfiguration"):
        apps.get_model("configuration", model_name).objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_from_env, unseed),
    ]