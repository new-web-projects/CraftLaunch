"""
PaymentVerificationService tests — the security-critical path. Real,
unmocked signature crypto is covered in test_signature_verification.py;
here the Razorpay client itself is mocked so each test can drive
exactly one failure mode (bad signature, wrong order, amount mismatch,
currency mismatch, ...) without needing a live gateway.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import razorpay.errors
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.payments.models import Payment, PaymentEvent, PaymentOrder, PaymentTransaction
from apps.payments.services import PaymentVerificationService

from .test_order_creation import PaymentFixtureMixin


def _razorpay_payment_entity(**overrides):
    base = {
        "id": "pay_MOCKED456",
        "order_id": "order_MOCKED123",
        "amount": 50000,
        "currency": "INR",
        "status": "captured",
        "method": "upi",
        "bank": None,
        "wallet": None,
        "vpa": "customer@upi",
        "card_id": None,
        "email": "customer@example.com",
        "contact": "+919999999999",
    }
    base.update(overrides)
    return base


class PaymentVerificationTests(PaymentFixtureMixin, TestCase):
    def _make_order(self, *, phase=Payment.Phase.ADVANCE_PAYMENT, amount=Decimal("500.00")):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=phase, amount=amount,
            currency="INR", status=Payment.Status.ORDER_CREATED,
        )
        return PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_MOCKED123", amount=amount,
            amount_paise=50000, currency="INR", receipt="test-receipt-1", status=PaymentOrder.Status.CREATED,
        )

    def _mock_client(self, *, signature_raises=False, payment_entity=None):
        client = MagicMock()
        if signature_raises:
            client.utility.verify_payment_signature.side_effect = razorpay.errors.SignatureVerificationError("bad sig")
        client.payment.fetch.return_value = payment_entity or _razorpay_payment_entity()
        return client

    def test_successful_verification_captures_payment(self):
        order = self._make_order()
        client = self._mock_client()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            payment = PaymentVerificationService.verify_payment(
                order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                razorpay_signature="whatever-the-mock-accepts-it", customer=self.customer,
            )
        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertIsNotNone(payment.captured_at)
        self.assertTrue(
            PaymentTransaction.objects.filter(razorpay_payment_id="pay_MOCKED456", status="CAPTURED").exists()
        )

    def test_authorized_but_not_captured_status(self):
        order = self._make_order()
        client = self._mock_client(payment_entity=_razorpay_payment_entity(status="authorized"))
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            payment = PaymentVerificationService.verify_payment(
                order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                razorpay_signature="sig", customer=self.customer,
            )
        self.assertEqual(payment.status, Payment.Status.AUTHORIZED)
        self.assertIsNone(payment.captured_at)

    def test_invalid_signature_is_rejected_and_not_captured(self):
        order = self._make_order()
        client = self._mock_client(signature_raises=True)
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            with self.assertRaises(ValidationError):
                PaymentVerificationService.verify_payment(
                    order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                    razorpay_signature="bad-signature", customer=self.customer,
                )
        order.payment.refresh_from_db()
        self.assertEqual(order.payment.status, Payment.Status.VERIFICATION_FAILED)
        self.assertNotEqual(order.payment.status, Payment.Status.CAPTURED)

    def test_verification_failure_creates_payment_event(self):
        order = self._make_order()
        client = self._mock_client(signature_raises=True)
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            with self.assertRaises(ValidationError):
                PaymentVerificationService.verify_payment(
                    order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                    razorpay_signature="bad", customer=self.customer,
                )
        self.assertTrue(
            PaymentEvent.objects.filter(
                payment=order.payment, event_type=PaymentEvent.EventType.VERIFICATION_FAILED
            ).exists()
        )

    def test_wrong_order_id_is_rejected(self):
        order = self._make_order()
        client = self._mock_client()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            with self.assertRaises(ValidationError):
                PaymentVerificationService.verify_payment(
                    order.id, razorpay_order_id="order_SOMETHING_ELSE", razorpay_payment_id="pay_MOCKED456",
                    razorpay_signature="sig", customer=self.customer,
                )
        client.utility.verify_payment_signature.assert_not_called()  # rejected before even trying the signature

    def test_amount_mismatch_is_rejected(self):
        order = self._make_order(amount=Decimal("500.00"))
        client = self._mock_client(payment_entity=_razorpay_payment_entity(amount=99999))  # not 50000
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            with self.assertRaises(ValidationError):
                PaymentVerificationService.verify_payment(
                    order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                    razorpay_signature="sig", customer=self.customer,
                )
        order.payment.refresh_from_db()
        self.assertEqual(order.payment.status, Payment.Status.VERIFICATION_FAILED)

    def test_currency_mismatch_is_rejected(self):
        order = self._make_order()
        client = self._mock_client(payment_entity=_razorpay_payment_entity(currency="USD"))
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            with self.assertRaises(ValidationError):
                PaymentVerificationService.verify_payment(
                    order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                    razorpay_signature="sig", customer=self.customer,
                )

    def test_payment_belonging_to_different_order_is_rejected(self):
        order = self._make_order()
        client = self._mock_client(payment_entity=_razorpay_payment_entity(order_id="order_SOME_OTHER_ORDER"))
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            with self.assertRaises(ValidationError):
                PaymentVerificationService.verify_payment(
                    order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                    razorpay_signature="sig", customer=self.customer,
                )

    def test_failed_razorpay_status_is_rejected(self):
        order = self._make_order()
        client = self._mock_client(payment_entity=_razorpay_payment_entity(status="failed"))
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            with self.assertRaises(ValidationError):
                PaymentVerificationService.verify_payment(
                    order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                    razorpay_signature="sig", customer=self.customer,
                )

    def test_wrong_customer_cannot_verify(self):
        order = self._make_order()
        client = self._mock_client()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            with self.assertRaises(ValidationError):
                PaymentVerificationService.verify_payment(
                    order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                    razorpay_signature="sig", customer=self.other_customer,
                )

    def test_duplicate_verification_is_idempotent(self):
        """A second verify call with the same (already-verified)
        payment_id shouldn't create a second PaymentTransaction row or
        error out destructively — update_or_create on
        razorpay_payment_id keyed uniqueness handles this."""
        order = self._make_order()
        client = self._mock_client()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            PaymentVerificationService.verify_payment(
                order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                razorpay_signature="sig", customer=self.customer,
            )
            PaymentVerificationService.verify_payment(
                order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                razorpay_signature="sig", customer=self.customer,
            )
        self.assertEqual(PaymentTransaction.objects.filter(razorpay_payment_id="pay_MOCKED456").count(), 1)

    def test_secret_never_appears_in_any_serialized_response(self):
        """Belt-and-suspenders check on top of
        PaymentOrderResponseSerializer/PaymentSerializer's field
        lists themselves excluding it — confirms the actual verified
        PaymentTransaction's stored raw_response never picked up a
        key_secret-shaped value even if Razorpay's fetch response
        happened to include one."""
        order = self._make_order()
        entity = _razorpay_payment_entity()
        entity["key_secret_leaked_by_mistake"] = "should-never-be-stored"
        client = self._mock_client(payment_entity=entity)
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            PaymentVerificationService.verify_payment(
                order.id, razorpay_order_id="order_MOCKED123", razorpay_payment_id="pay_MOCKED456",
                razorpay_signature="sig", customer=self.customer,
            )
        txn = PaymentTransaction.objects.get(razorpay_payment_id="pay_MOCKED456")
        self.assertNotIn("key_secret_leaked_by_mistake", txn.raw_response)
        self.assertNotIn("should-never-be-stored", str(txn.raw_response))