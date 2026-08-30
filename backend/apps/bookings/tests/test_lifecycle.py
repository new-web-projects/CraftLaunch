"""
Part 5 — project lifecycle tests: dashboards, accept/reject with
concurrency safety, the full transition graph, milestones, delivery,
revisions (including the revision-limit rule), cancellation
permissions, and that every action leaves the right timeline/
notification trail. Mirrors the fixture conventions already
established in test_permissions.py / test_booking_creation.py rather
than introducing a new style.
"""

from __future__ import annotations

import threading

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings import lifecycle
from apps.bookings.models import (
    Booking,
    BookingTimeline,
    DeveloperAssignment,
    NotificationEvent,
    ProjectDelivery,
    ProjectMilestone,
    RevisionRequest,
)
from apps.bookings.services import (
    BookingService,
    DeliveryService,
    MilestoneService,
    ProjectLifecycleService,
    RevisionService,
)
from apps.catalog.models import Package, ServiceCategory, WebsiteCategory

User = get_user_model()
VALID_PASSWORD = "Str0ng!Passw0rd"


class LifecycleFixtureMixin:
    """One customer, two developers (so accept/assignment tests have
    someone to be *unauthorized*), one admin, one published package
    with revision_count=2 (so the revision-limit tests have a real,
    small limit to exceed)."""

    def setUp(self):
        self.customer = User.objects.create_user(
            username="lc_cust", email="lc_cust@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.other_customer = User.objects.create_user(
            username="lc_cust2", email="lc_cust2@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.dev_a = User.objects.create_user(
            username="lc_deva", email="lc_deva@example.com", password=VALID_PASSWORD,
            role="DEVELOPER", is_active=True, is_email_verified=True,
        )
        self.dev_b = User.objects.create_user(
            username="lc_devb", email="lc_devb@example.com", password=VALID_PASSWORD,
            role="DEVELOPER", is_active=True, is_email_verified=True,
        )
        self.admin = User.objects.create_user(
            username="lc_admin", email="lc_admin@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )
        self.category = ServiceCategory.objects.create(name="LC Service", slug="lc-service")
        self.website_category = WebsiteCategory.objects.create(name="LC Website Cat", slug="lc-website-cat")
        self.package = Package.objects.create(
            service_category=self.category, tier="BASIC", name="LC Package",
            slug="lc-package", description="x", starting_price="500.00",
            delivery_days=10, revision_count=2, support_duration_days=30,
            status=Package.Status.PUBLISHED,
        )

    def _booking(self, customer=None):
        return BookingService.create_booking(
            customer=customer or self.customer, package=self.package, website_category=self.website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP", description="x",
        )

    def _awaiting_developer_booking(self, customer=None):
        """A booking already moved to the one status accept/reject
        actually operate on, via the real service path (submit()) —
        not by poking .status directly — so these tests also exercise
        the draft->submitted->awaiting_developer hop."""
        booking = self._booking(customer=customer)
        return BookingService.submit(booking, actor=booking.customer)

    def _accepted_booking(self, developer=None):
        booking = self._awaiting_developer_booking()
        return ProjectLifecycleService.accept_project(booking.id, developer=developer or self.dev_a)


# =====================================================================
# Transition graph — pure unit tests, no DB
# =====================================================================


class TransitionGraphTests(LifecycleFixtureMixin, APITestCase):
    def test_full_happy_path_is_all_valid_edges(self):
        path = [
            "draft", "submitted", "awaiting_developer", "accepted", "in_progress",
            "waiting_for_customer", "ready_for_delivery", "delivered", "completed",
        ]
        for from_code, to_code in zip(path, path[1:]):
            self.assertTrue(
                lifecycle.is_valid_transition(from_code, to_code),
                f"{from_code} -> {to_code} should be valid",
            )

    def test_revision_loop_is_valid(self):
        self.assertTrue(lifecycle.is_valid_transition("waiting_for_customer", "revision_requested"))
        self.assertTrue(lifecycle.is_valid_transition("revision_requested", "in_progress"))
        self.assertTrue(lifecycle.is_valid_transition("delivered", "revision_requested"))

    def test_skipping_states_is_invalid(self):
        self.assertFalse(lifecycle.is_valid_transition("draft", "completed"))
        self.assertFalse(lifecycle.is_valid_transition("accepted", "delivered"))
        self.assertFalse(lifecycle.is_valid_transition("awaiting_developer", "in_progress"))

    def test_terminal_statuses_have_no_outgoing_edges(self):
        for code in lifecycle.TERMINAL_STATUSES:
            self.assertEqual(lifecycle.TRANSITIONS.get(code, set()), set())

    def test_service_rejects_invalid_transition(self):
        booking = self._booking()
        with self.assertRaises(ValidationError):
            BookingService.transition_status(booking, "completed", actor=self.customer)

    def test_service_accepts_valid_transition_and_logs_timeline(self):
        booking = self._booking()
        before = booking.timeline_events.count()
        BookingService.transition_status(booking, "submitted", actor=self.customer)
        booking.refresh_from_db()
        self.assertEqual(booking.status.code, "submitted")
        self.assertEqual(booking.timeline_events.count(), before + 1)


# =====================================================================
# Accept / reject, and the concurrency-safety guarantee
# =====================================================================


class AcceptRejectTests(LifecycleFixtureMixin, APITestCase):
    def test_accept_assigns_developer_and_transitions_status(self):
        booking = self._awaiting_developer_booking()
        booking = ProjectLifecycleService.accept_project(booking.id, developer=self.dev_a)
        self.assertEqual(booking.status.code, "accepted")
        self.assertTrue(
            DeveloperAssignment.objects.filter(booking=booking, developer=self.dev_a, is_active=True).exists()
        )

    def test_accept_creates_milestones(self):
        booking = self._accepted_booking()
        self.assertEqual(booking.milestones.count(), len(ProjectMilestone.DEFAULT_STAGES))
        self.assertTrue(all(not m.is_completed for m in booking.milestones.all()))

    def test_accept_creates_timeline_and_notification(self):
        booking = self._awaiting_developer_booking()
        booking = ProjectLifecycleService.accept_project(booking.id, developer=self.dev_a)
        self.assertTrue(
            booking.timeline_events.filter(event_type=BookingTimeline.EventType.PROJECT_ACCEPTED).exists()
        )
        self.assertTrue(
            NotificationEvent.objects.filter(
                recipient=self.customer, event_type=NotificationEvent.EventType.DEVELOPER_ASSIGNED
            ).exists()
        )

    def test_second_accept_attempt_is_rejected(self):
        """Sequential re-attempt of the exact invariant
        select_for_update() protects: once a booking has an active
        assignment, a second accept must fail cleanly rather than
        silently creating a second one. A real simultaneous-thread race
        can't be asserted deterministically against the SQLite test
        backend (it has no true row-level locking), so this test
        verifies the logical guard the lock exists to protect, and
        test_db_constraint_blocks_two_active_assignments below verifies
        the DB-level backstop directly."""
        booking = self._awaiting_developer_booking()
        ProjectLifecycleService.accept_project(booking.id, developer=self.dev_a)
        with self.assertRaises(ValidationError):
            ProjectLifecycleService.accept_project(booking.id, developer=self.dev_b)
        self.assertEqual(DeveloperAssignment.objects.filter(booking=booking, is_active=True).count(), 1)

    def test_db_constraint_blocks_two_active_assignments(self):
        """Defense-in-depth: even bypassing the service entirely, the
        database itself refuses a second active assignment on one
        booking (unique_active_assignment_per_booking, models.py)."""
        booking = self._awaiting_developer_booking()
        DeveloperAssignment.objects.create(booking=booking, developer=self.dev_a, assigned_by=self.dev_a)
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            DeveloperAssignment.objects.create(booking=booking, developer=self.dev_b, assigned_by=self.dev_b)

    def test_cannot_accept_a_booking_not_awaiting_developer(self):
        booking = self._booking()  # still draft
        with self.assertRaises(ValidationError):
            ProjectLifecycleService.accept_project(booking.id, developer=self.dev_a)

    def test_reject_requires_a_reason(self):
        booking = self._awaiting_developer_booking()
        with self.assertRaises(ValidationError):
            ProjectLifecycleService.reject_project(booking.id, developer=self.dev_a, reason="")

    def test_reject_moves_to_rejected_and_notifies_customer(self):
        booking = self._awaiting_developer_booking()
        booking = ProjectLifecycleService.reject_project(
            booking.id, developer=self.dev_a, reason="Outside my area of expertise."
        )
        self.assertEqual(booking.status.code, "rejected")
        self.assertTrue(booking.status.is_terminal)
        self.assertTrue(
            NotificationEvent.objects.filter(
                recipient=self.customer, event_type=NotificationEvent.EventType.BOOKING_REJECTED
            ).exists()
        )

    # --- API-level permission checks ---

    def test_customer_cannot_accept_via_api(self):
        booking = self._awaiting_developer_booking()
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("bookings:accept", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_developer_accept_via_api(self):
        booking = self._awaiting_developer_booking()
        self.client.force_authenticate(self.dev_a)
        response = self.client.post(reverse("bookings:accept", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"]["code"], "accepted")


class ConcurrentAcceptThreadTests(LifecycleFixtureMixin, TransactionTestCase):
    """A genuine multi-threaded race, on top of the sequential
    guarantee already covered above. TransactionTestCase (not
    TestCase) is required so each thread gets its own real DB
    connection/transaction rather than sharing the outer test's
    uncommitted one. Threads are only used to exercise this path at
    all — the assertion is on the *outcome* (exactly one accept wins),
    which holds regardless of the underlying database's actual locking
    granularity."""

    def test_only_one_of_two_simultaneous_accepts_wins(self):
        booking = self._awaiting_developer_booking()
        results = {}

        def attempt(developer, key):
            try:
                ProjectLifecycleService.accept_project(booking.id, developer=developer)
                results[key] = "ok"
            except Exception:
                # Any failure here — our own ValidationError, or the
                # database's own locking error (SQLite raises a raw
                # OperationalError("database table is locked") rather
                # than waiting the way Postgres's row-level FOR UPDATE
                # would) — means this attempt didn't win. Either way
                # the outcome we actually care about is the final DB
                # state asserted below, which is mechanism-agnostic.
                results[key] = "did not win"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=(self.dev_a, "a"))
        t2 = threading.Thread(target=attempt, args=(self.dev_b, "b"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = list(results.values())
        self.assertEqual(outcomes.count("ok"), 1, f"expected exactly one winner, got {results}")
        self.assertEqual(
            DeveloperAssignment.objects.filter(booking_id=booking.id, is_active=True).count(), 1
        )


# =====================================================================
# Assigned-developer project management
# =====================================================================


class ProjectManagementTests(LifecycleFixtureMixin, APITestCase):
    def test_unassigned_developer_cannot_start(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.dev_b)
        response = self.client.post(reverse("bookings:start", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assigned_developer_can_start(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.dev_a)
        response = self.client.post(reverse("bookings:start", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"]["code"], "in_progress")

    def test_admin_can_start_any_project(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("bookings:start", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_milestone_completion_updates_progress(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.assertEqual(booking.progress_percent, 0)
        milestone = booking.milestones.first()
        MilestoneService.complete_milestone(milestone, actor=self.dev_a)
        booking.refresh_from_db()
        self.assertGreater(booking.progress_percent, 0)

    def test_milestone_update_via_api_requires_assignment(self):
        booking = self._accepted_booking(developer=self.dev_a)
        milestone = booking.milestones.first()
        url = reverse("bookings:milestone-update", args=[booking.id, milestone.id])
        self.client.force_authenticate(self.dev_b)
        response = self.client.patch(url, {"is_completed": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.dev_a)
        response = self.client.patch(url, {"is_completed": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_completed"])


# =====================================================================
# Delivery
# =====================================================================


class DeliveryTests(LifecycleFixtureMixin, APITestCase):
    def _in_progress_booking(self):
        booking = self._accepted_booking(developer=self.dev_a)
        return ProjectLifecycleService.start_project(booking, developer=self.dev_a)

    def _waiting_for_customer_booking(self):
        booking = self._in_progress_booking()
        return ProjectLifecycleService.mark_waiting_for_customer(booking, developer=self.dev_a)

    def test_cannot_submit_delivery_before_waiting_for_customer(self):
        booking = self._in_progress_booking()
        with self.assertRaises(ValidationError):
            DeliveryService.submit_delivery(booking, developer=self.dev_a, notes="done")

    def test_submit_delivery_transitions_and_records_details(self):
        booking = self._waiting_for_customer_booking()
        delivery = DeliveryService.submit_delivery(
            booking, developer=self.dev_a, notes="All done.",
            final_url="https://example.com", access_instructions="Use the admin login.",
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status.code, "delivered")
        self.assertEqual(delivery.final_url, "https://example.com")
        self.assertIsNotNone(delivery.delivered_at)
        self.assertTrue(
            booking.timeline_events.filter(event_type=BookingTimeline.EventType.DELIVERY_SUBMITTED).exists()
        )

    def test_customer_accepts_delivery_completes_project(self):
        booking = self._waiting_for_customer_booking()
        DeliveryService.submit_delivery(booking, developer=self.dev_a, notes="done")
        booking.refresh_from_db()
        booking = DeliveryService.accept_delivery(booking, customer=self.customer)
        self.assertEqual(booking.status.code, "completed")
        self.assertTrue(booking.status.is_terminal)
        delivery = ProjectDelivery.objects.get(booking=booking)
        self.assertIsNotNone(delivery.accepted_at)

    def test_completed_project_still_visible_to_developer(self):
        """Regression guard: completing a project must NOT flip
        DeveloperAssignment.is_active off, or the developer's own
        completed work would vanish from their own booking list (see
        DeliveryService.accept_delivery's comment)."""
        booking = self._waiting_for_customer_booking()
        DeliveryService.submit_delivery(booking, developer=self.dev_a, notes="done")
        booking.refresh_from_db()
        DeliveryService.accept_delivery(booking, customer=self.customer)
        self.assertTrue(Booking.objects.for_developer(self.dev_a).filter(pk=booking.pk).exists())

    def test_other_developer_cannot_submit_delivery(self):
        booking = self._waiting_for_customer_booking()
        self.client.force_authenticate(self.dev_b)
        response = self.client.post(reverse("bookings:delivery", args=[booking.id]), {"notes": "x"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_developer_cannot_accept_own_delivery(self):
        booking = self._waiting_for_customer_booking()
        DeliveryService.submit_delivery(booking, developer=self.dev_a, notes="done")
        booking.refresh_from_db()
        self.client.force_authenticate(self.dev_a)
        response = self.client.post(reverse("bookings:delivery-accept", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# =====================================================================
# Revisions, including the revision-limit rule
# =====================================================================


class RevisionTests(LifecycleFixtureMixin, APITestCase):
    def _delivered_booking(self):
        booking = self._accepted_booking(developer=self.dev_a)
        booking = ProjectLifecycleService.start_project(booking, developer=self.dev_a)
        booking = ProjectLifecycleService.mark_waiting_for_customer(booking, developer=self.dev_a)
        DeliveryService.submit_delivery(booking, developer=self.dev_a, notes="v1")
        booking.refresh_from_db()
        return booking

    def test_revision_request_requires_reason(self):
        booking = self._delivered_booking()
        with self.assertRaises(ValidationError):
            RevisionService.request_revision(booking, customer=self.customer, reason="")

    def test_revision_request_moves_status_and_notifies_developer(self):
        booking = self._delivered_booking()
        RevisionService.request_revision(booking, customer=self.customer, reason="Please change the header.")
        booking.refresh_from_db()
        self.assertEqual(booking.status.code, "revision_requested")
        self.assertTrue(
            NotificationEvent.objects.filter(
                recipient=self.dev_a, event_type=NotificationEvent.EventType.REVISION_REQUESTED
            ).exists()
        )

    def test_revisions_within_package_limit_are_pending(self):
        # self.package.revision_count == 2 (fixture)
        booking = self._delivered_booking()
        r1 = RevisionService.request_revision(booking, customer=self.customer, reason="Change 1.")
        self.assertEqual(r1.status, RevisionRequest.Status.PENDING)

        # Cycle back to a deliverable state for the 2nd round.
        booking.refresh_from_db()
        booking = ProjectLifecycleService.start_project(booking, developer=self.dev_a)
        booking = ProjectLifecycleService.mark_waiting_for_customer(booking, developer=self.dev_a)
        DeliveryService.submit_delivery(booking, developer=self.dev_a, notes="v2")
        booking.refresh_from_db()
        r2 = RevisionService.request_revision(booking, customer=self.customer, reason="Change 2.")
        self.assertEqual(r2.status, RevisionRequest.Status.PENDING)

    def test_revision_beyond_package_limit_is_flagged(self):
        booking = self._delivered_booking()
        for i in range(self.package.revision_count):
            RevisionRequest.objects.create(
                booking=booking, requested_by=self.customer, reason=f"Change {i}.",
                status=RevisionRequest.Status.PENDING,
            )
        # The (revision_count + 1)th request exceeds what the package
        # includes — must be flagged, not silently accepted as free.
        r = RevisionService.request_revision(booking, customer=self.customer, reason="One more change.")
        self.assertEqual(r.status, RevisionRequest.Status.LIMIT_EXCEEDED)

    def test_cannot_request_revision_in_progress(self):
        booking = self._accepted_booking(developer=self.dev_a)
        booking = ProjectLifecycleService.start_project(booking, developer=self.dev_a)
        with self.assertRaises(ValidationError):
            RevisionService.request_revision(booking, customer=self.customer, reason="Too early.")

    def test_other_customer_cannot_request_revision(self):
        booking = self._delivered_booking()
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(
            reverse("bookings:revisions", args=[booking.id]), {"reason": "Not my project."}
        )
        # for_user() scoping means a stranger's booking doesn't even
        # resolve for them — 404, not 403, same convention as every
        # other booking sub-resource (IsBookingParticipant's docstring).
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =====================================================================
# Cancellation permissions
# =====================================================================


class CancellationPermissionTests(LifecycleFixtureMixin, APITestCase):
    def test_owner_can_cancel(self):
        booking = self._booking()
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("bookings:cancel", args=[booking.id]), {"reason": "Changed plans."})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_customer_cannot_cancel(self):
        booking = self._booking()
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(reverse("bookings:cancel", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assigned_developer_cannot_cancel(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.dev_a)
        response = self.client.post(reverse("bookings:cancel", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancel_notifies_assigned_developer(self):
        booking = self._accepted_booking(developer=self.dev_a)
        BookingService.cancel(booking, actor=self.customer, reason="No longer needed.")
        self.assertTrue(
            NotificationEvent.objects.filter(
                recipient=self.dev_a, event_type=NotificationEvent.EventType.PROJECT_CANCELLED
            ).exists()
        )

    def test_cannot_cancel_after_delivery(self):
        """delivered has no outgoing edge to cancelled in the state
        graph — once delivered, the only forward moves are accept or
        request revision."""
        booking = self._accepted_booking(developer=self.dev_a)
        booking = ProjectLifecycleService.start_project(booking, developer=self.dev_a)
        booking = ProjectLifecycleService.mark_waiting_for_customer(booking, developer=self.dev_a)
        DeliveryService.submit_delivery(booking, developer=self.dev_a, notes="done")
        booking.refresh_from_db()
        with self.assertRaises(ValidationError):
            BookingService.cancel(booking, actor=self.customer)


# =====================================================================
# Dashboards — authorization and shape
# =====================================================================


class DashboardTests(LifecycleFixtureMixin, APITestCase):
    def test_customer_dashboard_requires_customer_role(self):
        self.client.force_authenticate(self.dev_a)
        response = self.client.get(reverse("bookings:dashboard-customer"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_developer_dashboard_requires_developer_role(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("bookings:dashboard-developer"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_dashboard_counts_only_own_bookings(self):
        self._booking(customer=self.customer)
        self._booking(customer=self.other_customer)
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("bookings:dashboard-customer"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["counts"]["pending_bookings"], 1)

    def test_developer_dashboard_shows_shared_request_pool_count(self):
        self._awaiting_developer_booking()
        self._awaiting_developer_booking()
        self.client.force_authenticate(self.dev_a)
        response = self.client.get(reverse("bookings:dashboard-developer"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["counts"]["new_project_requests"], 2)

    def test_unauthenticated_dashboard_access_denied(self):
        response = self.client.get(reverse("bookings:dashboard-customer"))
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


# =====================================================================
# Cross-cutting: a stranger can never reach a booking by guessing/
# editing its ID, on ANY Part 5 sub-resource.
# =====================================================================


class ObjectOwnershipTests(LifecycleFixtureMixin, APITestCase):
    def test_stranger_cannot_view_booking_detail(self):
        booking = self._booking()
        self.client.force_authenticate(self.other_customer)
        response = self.client.get(reverse("bookings:detail", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stranger_cannot_view_milestones(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.other_customer)
        response = self.client.get(reverse("bookings:milestones", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unassigned_developer_cannot_view_booking(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.dev_b)
        response = self.client.get(reverse("bookings:detail", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stranger_cannot_view_delivery(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.other_customer)
        response = self.client.get(reverse("bookings:delivery", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =====================================================================
# Feature flag wiring (Part 4's flag, finally read by something)
# =====================================================================


class BookingFeatureFlagTests(LifecycleFixtureMixin, APITestCase):
    def test_booking_creation_blocked_when_flag_disabled(self):
        from apps.configuration.models import FeatureFlags
        from apps.configuration.services import invalidate

        flags = FeatureFlags.load()
        flags.booking_enabled = False
        flags.save()
        invalidate(FeatureFlags)
        try:
            with self.assertRaises(ValidationError):
                self._booking()
        finally:
            flags.booking_enabled = True
            flags.save()
            invalidate(FeatureFlags)


# =====================================================================
# Multi-status list filtering (?status=a,b,c) — backs the dashboard
# stat-card links and the nav's status-scoped shortcuts.
# =====================================================================


class BookingStatusFilterTests(LifecycleFixtureMixin, APITestCase):
    def test_comma_separated_status_filter(self):
        draft = self._booking()
        awaiting = self._awaiting_developer_booking()
        self.client.force_authenticate(self.customer)

        response = self.client.get(reverse("bookings:list-create"), {"status": "draft,awaiting_developer"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {str(draft.id), str(awaiting.id)})

    def test_status_filter_excludes_non_matching(self):
        self._booking()  # draft — should be excluded below
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("bookings:list-create"), {"status": "completed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])


# =====================================================================
# Notes and requirements — previously-missing endpoints for
# already-existing service/model support (see views.py's comment).
# =====================================================================


class BookingNoteTests(LifecycleFixtureMixin, APITestCase):
    def test_participant_can_add_note(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.dev_a)
        response = self.client.post(reverse("bookings:notes", args=[booking.id]), {"content": "Kicking off tomorrow."})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(booking.notes.count(), 1)
        self.assertTrue(
            booking.timeline_events.filter(event_type=BookingTimeline.EventType.NOTE_ADDED).exists()
        )

    def test_non_staff_cannot_create_internal_note(self):
        """A developer marking is_internal=True is silently downgraded
        to a normal note, not rejected — see the view's `and
        request.user.is_staff` guard — since a non-staff internal-note
        *attempt* isn't a security event worth a hard error over."""
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.dev_a)
        self.client.post(
            reverse("bookings:notes", args=[booking.id]), {"content": "Trying to hide this", "is_internal": True}
        )
        note = booking.notes.get()
        self.assertFalse(note.is_internal)

    def test_internal_notes_hidden_from_customer_list(self):
        booking = self._accepted_booking(developer=self.dev_a)
        BookingService.add_note(booking, author=self.admin, content="Internal only", is_internal=True)
        BookingService.add_note(booking, author=self.customer, content="Visible note", is_internal=False)

        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("bookings:notes", args=[booking.id]))
        contents = [n["content"] for n in response.data]
        self.assertIn("Visible note", contents)
        self.assertNotIn("Internal only", contents)

    def test_stranger_cannot_add_note(self):
        booking = self._booking()
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(reverse("bookings:notes", args=[booking.id]), {"content": "x"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BookingRequirementUpdateTests(LifecycleFixtureMixin, APITestCase):
    def test_owner_can_add_requirement(self):
        booking = self._booking()
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("bookings:requirements", args=[booking.id]),
            {"title": "Add a newsletter signup", "description": "In the footer.", "priority": "HIGH"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(booking.customer_requirements.count(), 1)
        self.assertTrue(
            booking.timeline_events.filter(event_type=BookingTimeline.EventType.REQUIREMENTS_UPDATED).exists()
        )

    def test_other_customer_cannot_add_requirement(self):
        booking = self._booking()
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(reverse("bookings:requirements", args=[booking.id]), {"title": "x"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_developer_cannot_add_requirement(self):
        booking = self._accepted_booking(developer=self.dev_a)
        self.client.force_authenticate(self.dev_a)
        response = self.client.post(reverse("bookings:requirements", args=[booking.id]), {"title": "x"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_add_requirement_to_terminal_booking(self):
        booking = self._booking()
        BookingService.cancel(booking, actor=self.customer, reason="No longer needed.")
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("bookings:requirements", args=[booking.id]), {"title": "Too late"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =====================================================================
# Cancellation now requires a reason at the API layer (spec: "must
# require a reason"), while BookingService.cancel() itself stays
# lenient for direct/internal callers — see BookingCancelSerializer's
# docstring for the full reasoning.
# =====================================================================


class CancelReasonRequiredTests(LifecycleFixtureMixin, APITestCase):
    def test_cancel_without_reason_is_rejected(self):
        booking = self._booking()
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("bookings:cancel", args=[booking.id]), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_with_short_reason_is_rejected(self):
        booking = self._booking()
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("bookings:cancel", args=[booking.id]), {"reason": "no"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_with_reason_succeeds(self):
        booking = self._booking()
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("bookings:cancel", args=[booking.id]), {"reason": "Found a different developer."}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)