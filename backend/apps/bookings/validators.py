"""
Validators for booking creation: business name, website name, delivery
date, file type/size, and duplicate-submission protection. Kept
separate from serializers.py so the same rules are reusable from
services.py without importing DRF, and testable in isolation.
"""

import re
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

NAME_RE = re.compile(r"^[\w][\w\s&.,'\-]{1,148}[\w.,)]$", re.UNICODE)

MIN_DELIVERY_LEAD_DAYS = 3
MAX_DELIVERY_LEAD_DAYS = 365


def validate_business_name(value: str) -> None:
    value = (value or "").strip()
    if len(value) < 2:
        raise ValidationError("Business name must be at least 2 characters.")
    if not NAME_RE.match(value):
        raise ValidationError(
            "Business name may only contain letters, numbers, spaces and & . , ' -"
        )


def validate_website_name(value: str) -> None:
    value = (value or "").strip()
    if len(value) < 2:
        raise ValidationError("Website name must be at least 2 characters.")
    if not NAME_RE.match(value):
        raise ValidationError(
            "Website name may only contain letters, numbers, spaces and & . , ' -"
        )


def validate_preferred_delivery_date(value: date | None) -> None:
    if value is None:
        return
    today = timezone.localdate()
    if value < today + timedelta(days=MIN_DELIVERY_LEAD_DAYS):
        raise ValidationError(
            f"Preferred delivery date must be at least {MIN_DELIVERY_LEAD_DAYS} days from today."
        )
    if value > today + timedelta(days=MAX_DELIVERY_LEAD_DAYS):
        raise ValidationError("Preferred delivery date is too far in the future.")


def validate_reference_links(value) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise ValidationError("Reference links must be a list.")
    if len(value) > 10:
        raise ValidationError("No more than 10 reference links are allowed.")
    url_re = re.compile(r"^https?://[^\s]+\.[^\s]{2,}$")
    for item in value:
        if not isinstance(item, dict) or "url" not in item:
            raise ValidationError('Each reference link must be an object with a "url" field.')
        if not url_re.match(item["url"]):
            raise ValidationError(f"Not a valid URL: {item['url']!r}")


EXTENSION_TO_CATEGORY = {
    "jpg": "IMAGE", "jpeg": "IMAGE", "png": "IMAGE", "gif": "IMAGE", "webp": "IMAGE", "svg": "IMAGE",
    "pdf": "PDF",
    "zip": "ZIP",
    "doc": "DOCX", "docx": "DOCX",
    "xls": "SPREADSHEET", "xlsx": "SPREADSHEET", "csv": "SPREADSHEET",
    "txt": "TEXT",
}


def validate_attachment(filename: str, size_bytes: int) -> str:
    """Returns the resolved FileCategory on success, raises otherwise."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    allowed = {e.lower() for e in settings.BOOKING_ATTACHMENT_ALLOWED_EXTENSIONS}
    if ext not in allowed:
        raise ValidationError(
            f"'.{ext}' files are not allowed. Allowed types: {', '.join(sorted(allowed))}."
        )

    max_bytes = settings.BOOKING_ATTACHMENT_MAX_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationError(
            f"File is too large ({size_bytes / 1024 / 1024:.1f}MB). "
            f"Maximum is {settings.BOOKING_ATTACHMENT_MAX_SIZE_MB}MB."
        )
    if size_bytes <= 0:
        raise ValidationError("File appears to be empty.")

    return EXTENSION_TO_CATEGORY[ext]


def validate_rejection_reason(value: str) -> None:
    value = (value or "").strip()
    if len(value) < 5:
        raise ValidationError("A rejection reason is required.")


def validate_revision_reason(value: str) -> None:
    value = (value or "").strip()
    if len(value) < 5:
        raise ValidationError("A reason for the revision request is required.")


def check_duplicate_submission(idempotency_key: str | None) -> None:
    """Raises if a booking with this idempotency key already exists.
    Actual creation still relies on the DB-level unique constraint as
    the authoritative guard against a race between two concurrent
    identical requests — this is the fast, friendly pre-check."""
    if not idempotency_key:
        return
    from apps.bookings.models import Booking

    if Booking.all_objects.filter(idempotency_key=idempotency_key).exists():
        raise ValidationError(
            "This booking was already submitted.", code="duplicate_submission"
        )