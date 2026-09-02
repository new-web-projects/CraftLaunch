from decimal import Decimal

from django.test import TestCase

from apps.payments.models import Payment
from apps.payments.services import PaymentCalculationService

from .test_order_creation import PaymentFixtureMixin


class PaymentCalculationServiceTests(PaymentFixtureMixin, TestCase):
    def test_summary_before_any_payment(self):
        booking = self._accepted_booking()
        summary = PaymentCalculationService.get_project_summary(booking)
        self.assertEqual(summary["total_amount"], Decimal("1000.00"))
        self.assertEqual(summary["advance_amount"], Decimal("500.00"))
        self.assertEqual(summary["final_amount"], Decimal("500.00"))
        self.assertEqual(summary["amount_paid"], Decimal("0.00"))
        self.assertEqual(summary["amount_due"], Decimal("1000.00"))
        self.assertFalse(summary["is_advance_captured"])
        self.assertFalse(summary["is_final_captured"])

    def test_summary_after_advance_captured(self):
        booking = self._accepted_booking()
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        summary = PaymentCalculationService.get_project_summary(booking)
        self.assertEqual(summary["amount_paid"], Decimal("500.00"))
        self.assertEqual(summary["amount_due"], Decimal("500.00"))
        self.assertTrue(summary["is_advance_captured"])
        self.assertFalse(summary["is_final_captured"])

    def test_summary_after_both_captured(self):
        booking = self._accepted_booking()
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.FINAL_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        summary = PaymentCalculationService.get_project_summary(booking)
        self.assertEqual(summary["amount_paid"], Decimal("1000.00"))
        self.assertEqual(summary["amount_due"], Decimal("0.00"))
        self.assertTrue(summary["is_advance_captured"])
        self.assertTrue(summary["is_final_captured"])

    def test_pending_or_failed_payment_does_not_count_as_paid(self):
        booking = self._accepted_booking()
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.FAILED,
        )
        summary = PaymentCalculationService.get_project_summary(booking)
        self.assertEqual(summary["amount_paid"], Decimal("0.00"))
        self.assertFalse(summary["is_advance_captured"])

    def test_is_advance_captured_helper(self):
        booking = self._accepted_booking()
        self.assertFalse(PaymentCalculationService.is_advance_captured(booking))
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        self.assertTrue(PaymentCalculationService.is_advance_captured(booking))

    def test_snapshot_created_on_demand(self):
        booking = self._accepted_booking()
        snapshot = PaymentCalculationService.get_or_create_snapshot(booking)
        self.assertEqual(snapshot.agreed_price, Decimal("1000.00"))

    def test_snapshot_is_idempotent(self):
        booking = self._accepted_booking()
        first = PaymentCalculationService.get_or_create_snapshot(booking)
        second = PaymentCalculationService.get_or_create_snapshot(booking)
        self.assertEqual(first.id, second.id)