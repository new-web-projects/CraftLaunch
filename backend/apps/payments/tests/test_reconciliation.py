from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.payments.models import Payment, PaymentEvent, PaymentOrder
from apps.payments.services import ReconciliationService

from .test_order_creation import PaymentFixtureMixin


class ReconciliationTests(PaymentFixtureMixin, TestCase):
    def _make_payment_with_order(self, *, internal_status, razorpay_order_status):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=internal_status,
        )
        PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_RECONCILE1", amount=Decimal("500.00"),
            amount_paise=50000, currency="INR", receipt="recon-receipt-1", status=PaymentOrder.Status.CREATED,
        )
        client = MagicMock()
        client.order.fetch.return_value = {"id": "order_RECONCILE1", "status": razorpay_order_status}
        return payment, client

    def test_matching_states_log_reconciliation_ok(self):
        payment, client = self._make_payment_with_order(
            internal_status=Payment.Status.CAPTURED, razorpay_order_status="paid"
        )
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            result = ReconciliationService.reconcile(payment)
        self.assertTrue(result["match"])
        self.assertTrue(
            PaymentEvent.objects.filter(payment=payment, event_type=PaymentEvent.EventType.RECONCILIATION_OK).exists()
        )

    def test_mismatch_is_logged_not_silently_corrected(self):
        """Internal says captured, Razorpay says the order is still
        just 'created' — a real, if rare, mismatch. Must be flagged,
        and Payment.status must NOT be silently rewritten to match
        Razorpay's view."""
        payment, client = self._make_payment_with_order(
            internal_status=Payment.Status.CAPTURED, razorpay_order_status="created"
        )
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            result = ReconciliationService.reconcile(payment)

        self.assertFalse(result["match"])
        self.assertTrue(
            PaymentEvent.objects.filter(
                payment=payment, event_type=PaymentEvent.EventType.RECONCILIATION_MISMATCH
            ).exists()
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)  # unchanged — not auto-corrected

    def test_no_order_yet_returns_no_order_status(self):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CREATED,
        )
        result = ReconciliationService.reconcile(payment)
        self.assertEqual(result["status"], "no_order")
        self.assertIsNone(result["match"])