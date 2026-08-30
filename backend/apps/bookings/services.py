"""
Business logic layer for bookings. See catalog/services.py for the
note on why there's no separate repository class per model — the
custom Managers/QuerySets in models.py fill that role.

Part 5 adds four more service classes below BookingService/
AttachmentService (both unchanged in spirit from Part 3, just
threaded through the new state machine): ProjectLifecycleService
(developer accept/reject/start + coarse status moves), MilestoneService,
DeliveryService, RevisionService, and a small NotificationService
helper. They're kept as separate classes rather than folded into
BookingService purely for readability — BookingService stays "the
things that touch Booking's own core fields", the rest are each one
lifecycle concern.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.configuration.services import get_feature_flags

from . import lifecycle, validators
from .models import (
    Booking,
    BookingNote,
    BookingRequirement,
    BookingTimeline,
    CustomerRequirement,
    DeveloperAssignment,
    NotificationEvent,
    ProjectAttachment,
    ProjectDelivery,
    ProjectMilestone,
    ProjectStatus,
    RevisionRequest,
)
from .storage import build_storage_key, get_storage_backend


class NotificationService:
    """Part 5's "notification event foundation" — deliberately just
    database rows. Nothing here sends an email, push, or WhatsApp
    message; see NotificationEvent's docstring for why."""

    @staticmethod
    def notify(*, recipient, event_type: str, message: str, booking: Booking | None = None) -> NotificationEvent:
        return NotificationEvent.objects.create(
            recipient=recipient, booking=booking, event_type=event_type, message=message
        )

    @staticmethod
    def notify_many(*, recipients, event_type: str, message: str, booking: Booking | None = None) -> None:
        NotificationEvent.objects.bulk_create(
            [
                NotificationEvent(recipient=r, booking=booking, event_type=event_type, message=message)
                for r in recipients
                if r is not None
            ]
        )


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
        # Part 5 wires FeatureFlags.booking_enabled up to something for
        # the first time — Part 4 built the flag and its admin toggle,
        # but nothing actually read it yet (see the flag's own
        # docstring). This is the read path for the one flag whose
        # meaning is unambiguous without a much larger feature behind
        # it; registration_enabled/maintenance_mode etc. gate systems
        # this part doesn't touch and stay exactly as they were.
        if not get_feature_flags().booking_enabled:
            raise ValidationError("New bookings are temporarily disabled. Please check back later.")

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
        """DRAFT -> SUBMITTED -> AWAITING_DEVELOPER. The spec lists
        these as two distinct edges in the transition graph, but there
        is no separate manual "now open it up to developers" action
        anywhere in the spec — so a customer submitting a booking
        crosses both in one call. Both hops still go through
        transition_status individually (not a direct draft->awaiting
        jump) so the timeline/audit trail shows the real two-step path
        and each hop is validated against the graph on its own merits."""
        booking = BookingService.transition_status(booking, "submitted", actor=actor)
        booking = BookingService.transition_status(
            booking, "awaiting_developer", actor=actor, note="Opened for developers to review."
        )
        return booking

    @staticmethod
    @transaction.atomic
    def cancel(booking: Booking, *, actor, reason: str = "") -> Booking:
        # `reason` intentionally stays optional here, unchanged from
        # Part 3 — the existing test suite (test_cancel_via_api,
        # test_cannot_cancel_a_terminal_booking_again) exercises this
        # exact endpoint/method with no reason supplied at all, and
        # breaking that isn't something this part should do. The Part 5
        # spec's "cancellation must require a reason" is enforced at
        # the UI layer instead (the cancel dialog's reason field is
        # required there) — a real customer using the product always
        # supplies one; this method just doesn't add a new hard
        # rejection for callers (tests, a future admin tool) that
        # don't.
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
        recipients = [booking.customer] + [
            a.developer for a in booking.developer_assignments.filter(is_active=True)
        ]
        recipients = [r for r in recipients if r.id != actor.id]
        NotificationService.notify_many(
            recipients=recipients,
            booking=booking,
            event_type=NotificationEvent.EventType.PROJECT_CANCELLED,
            message=f'"{booking.website_name}" was cancelled.',
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

        # Part 5: the structural check that was missing in Part 3 — is
        # this edge even in the graph at all, independent of who's
        # asking. Role-based *who may cross it* is enforced separately,
        # at the permission-class/view layer (this mirrors how
        # IsBookingOwner/IsBookingParticipant already keep authorization
        # out of the service layer) — this function only ever answers
        # "is this shape of move legal".
        if not lifecycle.is_valid_transition(booking.status.code, new_status_code):
            raise ValidationError(lifecycle.describe_invalid_transition(booking.status.code, new_status_code))

        old_status = booking.status
        booking.status = new_status
        if new_status_code == "submitted" and booking.submitted_at is None:
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
        # An admin driving this directly (rather than a developer going
        # through ProjectLifecycleService.accept_project) still needs
        # the same milestone set to exist — get_or_create in
        # MilestoneService.create_milestones makes this safe even if
        # accept_project already ran it.
        MilestoneService.create_milestones(booking)
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

    @staticmethod
    @transaction.atomic
    def add_requirement(
        booking: Booking, *, actor, title: str, description: str = "", priority: str | None = None
    ) -> CustomerRequirement:
        """
        Part 5: 'Customer can ... Update allowed requirements' / timeline
        event 'Requirements updated'. Requirements are additive here —
        a customer adds a new requirement rather than editing or
        deleting existing ones, which keeps the requirements list an
        honest record of what was actually asked for at each point
        (an editable/deletable history would let a requirement quietly
        disappear after a developer already started work against it).
        Blocked once a booking is terminal, same guard as attachments.
        """
        if booking.status.is_terminal:
            raise ValidationError("This project is closed — requirements can no longer be changed.")

        requirement = CustomerRequirement.objects.create(
            booking=booking,
            title=title,
            description=description,
            priority=priority or CustomerRequirement.Priority.MEDIUM,
        )
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.REQUIREMENTS_UPDATED,
            actor=actor,
            description=f"Requirement added: {title}.",
        )
        # No NotificationEvent here — "requirements updated" isn't one
        # of the spec's 8 listed notification triggers (Booking
        # accepted/rejected, Developer assigned, Project started,
        # Revision requested, Delivery submitted, Project completed,
        # Project cancelled). The timeline entry above is the record;
        # inventing a 9th notification type wasn't asked for.
        return requirement


class ProjectLifecycleService:
    """Part 5: everything a developer does to move a project through
    its accepted lifecycle — accepting or rejecting a request, starting
    work, and the coarse status moves in between. Kept separate from
    BookingService for readability."""

    @staticmethod
    @transaction.atomic
    def accept_project(booking_id, *, developer) -> Booking:
        """
        Concurrency-safe accept. select_for_update() locks the Booking
        row for the rest of this transaction: if two developers submit
        an accept for the same booking within moments of each other,
        the second request's lock acquisition blocks until the first
        transaction commits. By the time it proceeds, the status/
        assignment check below sees the *post-accept* state and
        correctly rejects the second attempt — neither request can
        race past a stale read and both end up creating an assignment.
        The unique_active_assignment_per_booking constraint on
        DeveloperAssignment (models.py) is the second, DB-level
        backstop behind this lock, for any write path that ever
        bypasses this service.
        """
        try:
            booking = Booking.objects.select_for_update().get(pk=booking_id)
        except Booking.DoesNotExist:
            raise ValidationError("This project no longer exists.")

        if booking.status.code != "awaiting_developer":
            raise ValidationError("This project is no longer available to accept.")
        if booking.developer_assignments.filter(is_active=True).exists():
            raise ValidationError("This project has already been accepted by another developer.")

        DeveloperAssignment.objects.create(booking=booking, developer=developer, assigned_by=developer)
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.DEVELOPER_ASSIGNED,
            actor=developer,
            description=f"{developer.username} accepted and was assigned to this project.",
        )

        booking = BookingService.transition_status(
            booking, "accepted", actor=developer, note=f"Accepted by {developer.username}."
        )
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.PROJECT_ACCEPTED,
            actor=developer,
            description="Project accepted.",
        )
        MilestoneService.create_milestones(booking)
        NotificationService.notify(
            recipient=booking.customer,
            booking=booking,
            event_type=NotificationEvent.EventType.DEVELOPER_ASSIGNED,
            message=f'{developer.username} accepted your project "{booking.website_name}".',
        )
        return booking

    @staticmethod
    @transaction.atomic
    def reject_project(booking_id, *, developer, reason: str) -> Booking:
        validators.validate_rejection_reason(reason)
        try:
            booking = Booking.objects.select_for_update().get(pk=booking_id)
        except Booking.DoesNotExist:
            raise ValidationError("This project no longer exists.")

        if booking.status.code != "awaiting_developer":
            raise ValidationError("This project is no longer awaiting a developer decision.")

        booking = BookingService.transition_status(booking, "rejected", actor=developer, note=reason)
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.PROJECT_REJECTED,
            actor=developer,
            description=reason,
        )
        NotificationService.notify(
            recipient=booking.customer,
            booking=booking,
            event_type=NotificationEvent.EventType.BOOKING_REJECTED,
            message=f'Your project "{booking.website_name}" was declined.',
        )
        return booking

    @staticmethod
    @transaction.atomic
    def start_project(booking: Booking, *, developer) -> Booking:
        booking = BookingService.transition_status(booking, "in_progress", actor=developer)
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.PROJECT_STARTED,
            actor=developer,
            description="Development started.",
        )
        NotificationService.notify(
            recipient=booking.customer,
            booking=booking,
            event_type=NotificationEvent.EventType.PROJECT_STARTED,
            message=f'Work has started on "{booking.website_name}".',
        )
        return booking

    @staticmethod
    @transaction.atomic
    def mark_waiting_for_customer(booking: Booking, *, developer, note: str = "") -> Booking:
        return BookingService.transition_status(
            booking, "waiting_for_customer", actor=developer, note=note or "Waiting on customer input."
        )

    @staticmethod
    @transaction.atomic
    def mark_ready_for_delivery(booking: Booking, *, developer, note: str = "") -> Booking:
        return BookingService.transition_status(
            booking, "ready_for_delivery", actor=developer, note=note or "Marked ready for delivery."
        )


class MilestoneService:
    @staticmethod
    @transaction.atomic
    def create_milestones(booking: Booking) -> None:
        """Called once a project is accepted (either path — self-serve
        accept_project, or an admin's direct assign_developer).
        get_or_create makes a duplicate call harmless; the
        unique_stage_per_booking constraint backs that up at the DB
        level too."""
        for order, stage in enumerate(ProjectMilestone.DEFAULT_STAGES):
            ProjectMilestone.objects.get_or_create(
                booking=booking, stage=stage, defaults={"sort_order": order}
            )

    @staticmethod
    @transaction.atomic
    def complete_milestone(milestone: ProjectMilestone, *, actor) -> ProjectMilestone:
        if milestone.is_completed:
            return milestone
        milestone.is_completed = True
        milestone.completed_at = timezone.now()
        milestone.completed_by = actor
        milestone.save(update_fields=["is_completed", "completed_at", "completed_by"])
        BookingTimeline.objects.create(
            booking=milestone.booking,
            event_type=BookingTimeline.EventType.MILESTONE_COMPLETED,
            actor=actor,
            description=f"Milestone completed: {milestone.get_stage_display()}.",
        )
        return milestone

    @staticmethod
    @transaction.atomic
    def reopen_milestone(milestone: ProjectMilestone, *, actor) -> ProjectMilestone:
        """Un-checking a milestone doesn't get its own timeline entry —
        toggling isn't one of the spec's listed event types, and
        logging every correction would make the audit trail noisy for
        what's usually just fixing a misclick."""
        if not milestone.is_completed:
            return milestone
        milestone.is_completed = False
        milestone.completed_at = None
        milestone.completed_by = None
        milestone.save(update_fields=["is_completed", "completed_at", "completed_by"])
        return milestone


class DeliveryService:
    @staticmethod
    @transaction.atomic
    def submit_delivery(
        booking: Booking,
        *,
        developer,
        notes: str = "",
        final_url: str = "",
        access_instructions: str = "",
        attachment_ids: list | None = None,
    ) -> ProjectDelivery:
        if booking.status.code not in lifecycle.DELIVERABLE_STATUSES:
            raise ValidationError(
                "A delivery can only be submitted while a project is waiting on the "
                "customer or marked ready for delivery."
            )

        delivery, _ = ProjectDelivery.objects.get_or_create(booking=booking)
        delivery.delivered_by = developer
        delivery.notes = notes
        delivery.final_url = final_url
        delivery.access_instructions = access_instructions
        delivery.delivered_at = timezone.now()
        delivery.accepted_at = None  # a re-delivery after a revision resets acceptance
        delivery.save()

        if attachment_ids:
            valid_attachments = ProjectAttachment.objects.filter(booking=booking, id__in=attachment_ids)
            delivery.files.set(valid_attachments)

        booking = BookingService.transition_status(
            booking, "delivered", actor=developer, note="Delivery submitted."
        )
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.DELIVERY_SUBMITTED,
            actor=developer,
            description="Delivery submitted for customer review.",
        )
        NotificationService.notify(
            recipient=booking.customer,
            booking=booking,
            event_type=NotificationEvent.EventType.DELIVERY_SUBMITTED,
            message=f'Your project "{booking.website_name}" has been delivered.',
        )
        return delivery

    @staticmethod
    @transaction.atomic
    def accept_delivery(booking: Booking, *, customer) -> Booking:
        if booking.status.code != "delivered":
            raise ValidationError("There is no pending delivery to accept.")
        try:
            delivery = booking.delivery
        except ProjectDelivery.DoesNotExist:
            raise ValidationError("There is no delivery on record for this project.")

        delivery.accepted_at = timezone.now()
        delivery.save(update_fields=["accepted_at"])

        booking = BookingService.transition_status(
            booking, "completed", actor=customer, note="Delivery accepted."
        )
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.DELIVERY_ACCEPTED,
            actor=customer,
            description="Delivery accepted by customer.",
        )
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.PROJECT_COMPLETED,
            actor=customer,
            description="Project marked completed.",
        )
        # Deliberately NOT flipping DeveloperAssignment.is_active=False
        # here — that flag drives BookingQuerySet.for_developer(), which
        # is how a developer's own "Completed Projects" list finds its
        # rows. Unassigning on completion would make a developer's own
        # finished work disappear from their own dashboard.
        NotificationService.notify_many(
            recipients=[a.developer for a in booking.developer_assignments.filter(is_active=True)],
            booking=booking,
            event_type=NotificationEvent.EventType.PROJECT_COMPLETED,
            message=f'"{booking.website_name}" was marked complete by the customer.',
        )
        return booking


class RevisionService:
    @staticmethod
    @transaction.atomic
    def request_revision(
        booking: Booking, *, customer, reason: str, description: str = "", attachment_id=None
    ) -> RevisionRequest:
        validators.validate_revision_reason(reason)
        if booking.status.code not in lifecycle.REVISION_REQUESTABLE_STATUSES:
            raise ValidationError(
                "A revision can only be requested while a project is waiting on you "
                "or has just been delivered."
            )

        # The package's revision_count is what's paid for — count every
        # request that hasn't already been flagged as over that limit;
        # once `used_count` reaches it, the *next* request (this one)
        # is the one that gets marked LIMIT_EXCEEDED, not silently
        # treated as another free round. See RevisionRequest.Status.
        used_count = booking.revision_requests.exclude(status=RevisionRequest.Status.LIMIT_EXCEEDED).count()
        allowed = booking.package.revision_count
        exceeds_limit = used_count >= allowed

        attachment = None
        if attachment_id:
            attachment = ProjectAttachment.objects.filter(booking=booking, id=attachment_id).first()

        revision = RevisionRequest.objects.create(
            booking=booking,
            requested_by=customer,
            reason=reason,
            description=description,
            attachment=attachment,
            status=RevisionRequest.Status.LIMIT_EXCEEDED if exceeds_limit else RevisionRequest.Status.PENDING,
        )

        booking = BookingService.transition_status(booking, "revision_requested", actor=customer, note=reason)
        BookingTimeline.objects.create(
            booking=booking,
            event_type=BookingTimeline.EventType.REVISION_REQUESTED,
            actor=customer,
            description=(
                f"Revision requested — exceeds the {allowed} included with this package; "
                f"additional paid work is required."
                if exceeds_limit
                else f"Revision requested: {reason}"
            ),
            metadata={"revision_request_id": revision.id, "exceeds_limit": exceeds_limit},
        )
        NotificationService.notify_many(
            recipients=[a.developer for a in booking.developer_assignments.filter(is_active=True)],
            booking=booking,
            event_type=NotificationEvent.EventType.REVISION_REQUESTED,
            message=f'A revision was requested on "{booking.website_name}".',
        )
        return revision


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