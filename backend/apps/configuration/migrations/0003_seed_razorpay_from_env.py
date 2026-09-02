"""
Completes what 0002_seed_from_env.py's docstring flagged as reserved:
RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET are
now real Django settings (config/settings/base.py), so
PaymentConfiguration's first row can be seeded from them the same way
StorageConfiguration and EmailConfiguration already are — Part 6
bootstrapping test-mode credentials locally without anyone having to
click through the admin settings UI first.

Kept as its own additive migration rather than editing the
already-applied 0002, for the same reason bookings' status seeding
got its own follow-up migration instead of rewriting history.
"""

from django.conf import settings
from django.db import migrations


def seed_razorpay_from_env(apps, schema_editor):
    PaymentConfiguration = apps.get_model("configuration", "PaymentConfiguration")

    key_id = getattr(settings, "RAZORPAY_KEY_ID", None) or ""
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", None) or ""
    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None) or ""

    PaymentConfiguration.objects.get_or_create(
        pk=1,
        defaults={
            # Configured but left OFF by default even when credentials
            # are present — an admin flips is_enabled once they've
            # actually verified test-mode checkout works end to end,
            # rather than payments silently going live the moment
            # someone sets three env vars.
            "is_enabled": False,
            "mode": "SANDBOX",
            "razorpay_key_id": key_id,
            "razorpay_key_secret": key_secret,
            "razorpay_webhook_secret": webhook_secret,
            "default_currency": "INR",
        },
    )


def unseed(apps, schema_editor):
    # Nothing to reverse — 0002's own reverse (or 0001's, further
    # back) already deletes the PaymentConfiguration row entirely if
    # migrations are unwound that far; this migration only ever
    # touched fields on a row 0002 either already created or this
    # migration itself created via get_or_create.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0002_seed_from_env"),
    ]

    operations = [
        migrations.RunPython(seed_razorpay_from_env, unseed),
    ]