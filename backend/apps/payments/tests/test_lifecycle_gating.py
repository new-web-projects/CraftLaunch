"""
Tests for the one integration point between Part 5 and Part 6:
apps.bookings.services.ProjectLifecycleService.start_project and
DeliveryService.accept_delivery now check payment capture — but only
when FeatureFlags.payments_enabled is on. Both states are tested
explicitly, since "off" (the default) is what makes this addition
backward-compatible with every Part 5 test that predates payments.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.bookings.services import DeliveryService, ProjectLifecycleService
from apps.configuration.models import FeatureFlags
from apps.configuration.services import invalidate
from apps.payments.models import Payment

from .test_order_creation import PaymentFixtureMixin


class LifecycleGatingTests(PaymentFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.flags = FeatureFlags.load()

    def _set_payments_enabled(self, value: bool):
        self.flags.payments_enabled = value
        self.flags.save()
        invalidate(FeatureFlags)

    def tearDown(self):
        self._set_payments_enabled(False)  # restore the default for any other test module
        super().tearDown()

    def test_start_project_unaffected_when_payments_disabled(self):
        """The default state — payments_enabled=False — must behave
        exactly like Part 5, with no captured payment anywhere."""
        self._set_payments_enabled(False)
        booking = self._accepted_booking()
        booking = ProjectLifecycleService.start_project(booking, developer=self.developer)
        self.assertEqual(booking.status.code, "in_progress")

    def test_start_project_blocked_without_advance_payment_when_enabled(self):
        self._set_payments_enabled(True)
        booking = self._accepted_booking()
        with self.assertRaises(ValidationError):
            ProjectLifecycleService.start_project(booking, developer=self.developer)

    def test_start_project_succeeds_with_captured_advance_payment(self):
        self._set_payments_enabled(True)
        booking = self._accepted_booking()
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        booking = ProjectLifecycleService.start_project(booking, developer=self.developer)
        self.assertEqual(booking.status.code, "in_progress")

    def test_accept_delivery_unaffected_when_payments_disabled(self):
        self._set_payments_enabled(False)
        booking = self._accepted_booking()
        booking = ProjectLifecycleService.start_project(booking, developer=self.developer)
        booking = ProjectLifecycleService.mark_waiting_for_customer(booking, developer=self.developer)
        DeliveryService.submit_delivery(booking, developer=self.developer, notes="done")
        booking.refresh_from_db()
        booking = DeliveryService.accept_delivery(booking, customer=self.customer)
        self.assertEqual(booking.status.code, "completed")

    def test_accept_delivery_blocked_without_final_payment_when_enabled(self):
        self._set_payments_enabled(True)
        booking = self._accepted_booking()
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        booking = ProjectLifecycleService.start_project(booking, developer=self.developer)
        booking = ProjectLifecycleService.mark_waiting_for_customer(booking, developer=self.developer)
        DeliveryService.submit_delivery(booking, developer=self.developer, notes="done")
        booking.refresh_from_db()

        with self.assertRaises(ValidationError):
            DeliveryService.accept_delivery(booking, customer=self.customer)

    def test_accept_delivery_succeeds_with_both_payments_captured(self):
        self._set_payments_enabled(True)
        booking = self._accepted_booking()
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        booking = ProjectLifecycleService.start_project(booking, developer=self.developer)
        booking = ProjectLifecycleService.mark_waiting_for_customer(booking, developer=self.developer)
        DeliveryService.submit_delivery(booking, developer=self.developer, notes="done")
        booking.refresh_from_db()
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.FINAL_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )

        booking = DeliveryService.accept_delivery(booking, customer=self.customer)
        self.assertEqual(booking.status.code, "completed")