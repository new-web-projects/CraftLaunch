"""
Business logic layer for bookings. See catalog/services.py for the
note on why there's no separate repository class per model — the
custom Managers/QuerySets in models.py fill that role.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from . import validators
from .models import (
    Booking,
    BookingNote,
    BookingRequirement,
    BookingTimeline,
    CustomerRequirement,
    DeveloperAssignment,
    ProjectAttachment,
    ProjectStatus,
)
from .storage import build_storage_key, get_storage_backend


class BookingService:
    @staticmethod
    @transaction.atomic
    def create_booking(
        *,
        customer,
        package,
        website_category,
        website_type=None,
        website_name: str,
        business_name: str,
        business_type: str,
        description: str,
        preferred_delivery_date=None,
        reference_links=None,
        required_feature_ids: list | None = None,
        custom_requirements: list[dict] | None = None,
        idempotency_key: str | None = None,
    ) -> Booking:
        validators.validate_website_name(website_name)
        validators.validate_business_name(business_name)
        validators.validate_preferred_delivery_date(preferred_delivery_date)
        validators.validate_reference_links(reference_links)
        validators.check_duplicate_submission(idempotency_key)

        booking = Booking.objects.create(
            customer=customer,
            package=package,
            website_category=website_category,
            website_type=website_type,
            status=ProjectStatus.get_default(),
            website_name=website_name.strip(),
            business_name=business_name.strip(),
            business_type=business_type,
            description=description,
            preferred_delivery_date=preferred_delivery_date,
            reference_links=reference_links or [],
            idempotency_key=idempotency_key,
        )

        for feature_id in required_feature_ids or []:
            BookingRequirement.objects.create(booking=booking, website_feature_id=feature_id)

        for req in custom_requirements or []:
            CustomerRequirement.objects.create(
                booking=booking,
                title=req["title"],
                description=req.get("description", ""),
                priority=req.get("priority", CustomerRequirement.Priority.MEDIUM),
            )

        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.BOOKING_CREATED,
            actor=customer,
            to_status=booking.status,
            description=f"Booking created for {booking.website_name}.",
        )

        return booking

    @staticmethod
    @transaction.atomic
    def submit(booking: Booking, *, actor) -> Booking:
        return BookingService.transition_status(booking, "submitted", actor=actor)

    @staticmethod
    @transaction.atomic
    def cancel(booking: Booking, *, actor, reason: str = "") -> Booking:
        if booking.status.is_terminal:
            raise ValidationError(
                f"Booking is already {booking.status.label} and cannot be cancelled."
            )
        booking = BookingService.transition_status(booking, "cancelled", actor=actor, note=reason)
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.BOOKING_CANCELLED,
            actor=actor,
            description=reason or "Booking cancelled.",
        )
        return booking

    @staticmethod
    @transaction.atomic
    def transition_status(booking: Booking, new_status_code: str, *, actor, note: str = "") -> Booking:
        if booking.status.is_terminal:
            raise ValidationError(
                f"Booking is {booking.status.label}, which is a final status — no further "
                f"transitions are possible."
            )

        try:
            new_status = ProjectStatus.objects.get(code=new_status_code)
        except ProjectStatus.DoesNotExist:
            raise ValidationError(f"Unknown status code: {new_status_code!r}")

        old_status = booking.status
        booking.status = new_status
        if new_status_code == "submitted" and booking.submitted_at is None:
            from django.utils import timezone

            booking.submitted_at = timezone.now()
            booking.save(update_fields=["status", "submitted_at", "updated_at"])
        else:
            booking.save(update_fields=["status", "updated_at"])

        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.STATUS_CHANGED,
            actor=actor,
            from_status=old_status,
            to_status=new_status,
            description=note or f"Status changed from {old_status.label} to {new_status.label}.",
        )
        return booking

    @staticmethod
    @transaction.atomic
    def assign_developer(booking: Booking, developer, *, assigned_by, role_note: str = "") -> DeveloperAssignment:
        assignment = DeveloperAssignment.objects.create(
            booking=booking, developer=developer, assigned_by=assigned_by, role_note=role_note
        )
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.DEVELOPER_ASSIGNED,
            actor=assigned_by,
            description=f"{developer.username} assigned to this booking.",
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def add_note(booking: Booking, *, author, content: str, is_internal: bool = False) -> BookingNote:
        note = BookingNote.objects.create(
            booking=booking, author=author, content=content, is_internal=is_internal
        )
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.NOTE_ADDED,
            actor=author,
            description="Internal note added." if is_internal else "Note added.",
        )
        return note


class AttachmentService:
    @staticmethod
    @transaction.atomic
    def upload(booking: Booking, *, uploaded_by, file, filename: str, content_type: str) -> ProjectAttachment:
        file_category = validators.validate_attachment(filename, file.size)

        backend = get_storage_backend()
        key = build_storage_key(booking.id, filename)
        stored = backend.save(key, file, content_type)

        attachment = ProjectAttachment.objects.create(
            booking=booking,
            uploaded_by=uploaded_by,
            storage_provider=stored.provider,
            storage_key=stored.key,
            original_filename=filename,
            content_type=content_type,
            file_category=file_category,
            file_size=file.size,
        )
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.FILE_UPLOADED,
            actor=uploaded_by,
            description=f"Uploaded {filename}.",
        )
        return attachment

    @staticmethod
    @transaction.atomic
    def delete(attachment: ProjectAttachment, *, actor) -> None:
        backend = get_storage_backend()
        try:
            backend.delete(attachment.storage_key)
        except Exception:
            # Storage-side delete failing shouldn't block the record
            # from being marked deleted — soft delete means it's
            # already hidden from every normal query either way; a
            # background reconciliation job (future work) can retry
            # the actual provider-side cleanup.
            pass

        attachment.soft_delete()
        BookingTimeline.objects.create(
            booking=attachment.booking,
            event_type=BookingTimeline.EventType.FILE_DELETED,
            actor=actor,
            description=f"Deleted {attachment.original_filename}.",
        )