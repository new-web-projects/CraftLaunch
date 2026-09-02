"""
WebhookService tests. Signatures are computed for real (same HMAC as
test_signature_verification.py) rather than mocked — webhook signature
verification is a pure function of (body, secret), so there's no
reason not to exercise the actual crypto here too.
"""

import hashlib
import hmac
import json
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.payments.models import (
    Payment,
    PaymentEvent,
    PaymentOrder,
    PaymentTransaction,
    Refund,
    WebhookEvent,
)
from apps.payments.services import WebhookService

from .test_order_creation import PaymentFixtureMixin

WEBHOOK_SECRET = "dummy_webhook_secret"  # matches PaymentFixtureMixin's PaymentConfiguration setup


def _signed_body(payload: dict) -> tuple[str, str]:
    body = json.dumps(payload)
    signature = hmac.new(WEBHOOK_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body, signature


def _payment_captured_payload(*, order_id="order_MOCKED123", payment_id="pay_MOCKED456", amount=50000, currency="INR"):
    return {
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id, "order_id": order_id, "amount": amount,
                    "currency": currency, "status": "captured", "method": "upi",
                }
            }
        },
        "created_at": 1700000000,
    }


class WebhookIdempotencyTests(PaymentFixtureMixin, TestCase):
    def _make_order(self):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.ORDER_CREATED,
        )
        return PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_MOCKED123", amount=Decimal("500.00"),
            amount_paise=50000, currency="INR", receipt="wh-receipt-1", status=PaymentOrder.Status.CREATED,
        )

    def test_valid_webhook_is_processed_and_captures_payment(self):
        self._make_order()
        body, signature = _signed_body(_payment_captured_payload())
        WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_001")

        payment = Payment.objects.get(booking__isnull=False, phase=Payment.Phase.ADVANCE_PAYMENT)
        self.assertEqual(payment.status, Payment.Status.CAPTURED)

    def test_invalid_signature_is_rejected(self):
        self._make_order()
        body, _ = _signed_body(_payment_captured_payload())
        with self.assertRaises(ValidationError):
            WebhookService.process_webhook(raw_body=body, signature="totally-wrong-signature", event_id="evt_002")

    def test_invalid_signature_still_records_webhook_event(self):
        """The exact bug caught during development: a blanket
        @transaction.atomic around the whole method rolled this row
        back the moment the ValidationError propagated. Regression
        guard."""
        self._make_order()
        body, _ = _signed_body(_payment_captured_payload())
        with self.assertRaises(ValidationError):
            WebhookService.process_webhook(raw_body=body, signature="wrong", event_id="evt_003")

        event = WebhookEvent.objects.get(razorpay_event_id="evt_003")
        self.assertFalse(event.signature_verified)
        self.assertFalse(event.processed)
        self.assertTrue(event.error_message)

    def test_verification_failure_logs_payment_event(self):
        body, _ = _signed_body(_payment_captured_payload())
        with self.assertRaises(ValidationError):
            WebhookService.process_webhook(raw_body=body, signature="wrong", event_id="evt_004")
        self.assertTrue(
            PaymentEvent.objects.filter(event_type=PaymentEvent.EventType.WEBHOOK_VERIFICATION_FAILED).exists()
        )

    def test_duplicate_event_id_is_not_reprocessed(self):
        """Razorpay retries deliveries — a second call with the same
        x-razorpay-event-id must be a no-op, not a second capture
        attempt or a duplicate PaymentTransaction."""
        self._make_order()
        body, signature = _signed_body(_payment_captured_payload())
        WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_005")
        WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_005")

        self.assertEqual(WebhookEvent.objects.filter(razorpay_event_id="evt_005").count(), 1)
        self.assertEqual(PaymentTransaction.objects.filter(razorpay_payment_id="pay_MOCKED456").count(), 1)

    def test_missing_event_id_is_rejected(self):
        body, signature = _signed_body(_payment_captured_payload())
        with self.assertRaises(ValidationError):
            WebhookService.process_webhook(raw_body=body, signature=signature, event_id="")

    def test_webhook_for_unknown_order_does_not_error(self):
        """No PaymentOrder matches — this should be logged and
        ignored, not raise, since Razorpay will just keep retrying an
        error response forever."""
        body, signature = _signed_body(_payment_captured_payload(order_id="order_NEVER_CREATED"))
        event = WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_006")
        self.assertTrue(event.processed)

    def test_amount_mismatch_does_not_capture(self):
        self._make_order()
        body, signature = _signed_body(_payment_captured_payload(amount=999999))
        WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_007")
        payment = Payment.objects.get(phase=Payment.Phase.ADVANCE_PAYMENT)
        self.assertNotEqual(payment.status, Payment.Status.CAPTURED)
        self.assertTrue(
            PaymentEvent.objects.filter(event_type=PaymentEvent.EventType.RECONCILIATION_MISMATCH).exists()
        )


class WebhookPaymentFailedTests(PaymentFixtureMixin, TestCase):
    def test_payment_failed_event_marks_payment_failed(self):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.ORDER_CREATED,
        )
        PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_FAILCASE", amount=Decimal("500.00"),
            amount_paise=50000, currency="INR", receipt="wh-receipt-fail", status=PaymentOrder.Status.CREATED,
        )
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_FAILED1", "order_id": "order_FAILCASE",
                        "error_code": "BAD_REQUEST_ERROR", "error_description": "Insufficient funds.",
                    }
                }
            },
        }
        body, signature = _signed_body(payload)
        WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_fail_1")

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(payment.failure_reason, "Insufficient funds.")

    def test_failed_event_does_not_downgrade_already_captured_payment(self):
        """An out-of-order/late payment.failed arriving after a
        genuine capture (already handled via the synchronous verify
        endpoint) must not un-capture anything."""
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_ALREADYCAPTURED", amount=Decimal("500.00"),
            amount_paise=50000, currency="INR", receipt="wh-receipt-cap", status=PaymentOrder.Status.PAID,
        )
        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"id": "pay_LATE", "order_id": "order_ALREADYCAPTURED"}}},
        }
        body, signature = _signed_body(payload)
        WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_late_1")

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)


class WebhookRefundTests(PaymentFixtureMixin, TestCase):
    def test_refund_processed_webhook_creates_refund_record(self):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        order = PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_REFUNDCASE", amount=Decimal("500.00"),
            amount_paise=50000, currency="INR", receipt="wh-receipt-refund", status=PaymentOrder.Status.PAID,
        )
        PaymentTransaction.objects.create(
            payment_order=order, razorpay_payment_id="pay_REFUNDED1", status=PaymentTransaction.Status.CAPTURED,
        )
        payload = {
            "event": "refund.processed",
            "payload": {
                "refund": {"entity": {"id": "rfnd_001", "payment_id": "pay_REFUNDED1", "amount": 50000}}
            },
        }
        body, signature = _signed_body(payload)
        WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_refund_1")

        self.assertTrue(Refund.objects.filter(razorpay_refund_id="rfnd_001", status=Refund.Status.PROCESSED).exists())
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.REFUNDED)  # full refund (amount == payment.amount)

    def test_partial_refund_marks_partially_refunded(self):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        order = PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_PARTIALREFUND", amount=Decimal("500.00"),
            amount_paise=50000, currency="INR", receipt="wh-receipt-partial", status=PaymentOrder.Status.PAID,
        )
        PaymentTransaction.objects.create(
            payment_order=order, razorpay_payment_id="pay_PARTIAL1", status=PaymentTransaction.Status.CAPTURED,
        )
        payload = {
            "event": "refund.processed",
            "payload": {"refund": {"entity": {"id": "rfnd_002", "payment_id": "pay_PARTIAL1", "amount": 20000}}},
        }
        body, signature = _signed_body(payload)
        WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_refund_2")

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PARTIALLY_REFUNDED)