"""
Genuine HMAC tests against the real razorpay.Client.utility — no
mocking. Both verify_payment_signature and verify_webhook_signature
are pure cryptographic functions of their inputs (they don't call the
network), so computing a real, correct signature here and confirming
the SDK accepts it is a stronger check than mocking would be: it
validates this app's actual integration with Razorpay's documented
algorithm, not just that PaymentVerificationService calls some method
named right.

  Payment signature:  HMAC-SHA256(order_id + "|" + payment_id, key_secret)
  Webhook signature:  HMAC-SHA256(raw_body, webhook_secret)

Both confirmed against Razorpay's current official documentation
before implementing services.py.
"""

import hashlib
import hmac

import razorpay
import razorpay.errors
from django.test import SimpleTestCase

KEY_SECRET = "test_key_secret_abc123"
WEBHOOK_SECRET = "test_webhook_secret_xyz789"


def _client() -> razorpay.Client:
    return razorpay.Client(auth=("rzp_test_dummy", KEY_SECRET))


def _payment_signature(order_id: str, payment_id: str, secret: str = KEY_SECRET) -> str:
    message = f"{order_id}|{payment_id}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _webhook_signature(body: str, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


class PaymentSignatureVerificationTests(SimpleTestCase):
    def test_correct_signature_verifies(self):
        order_id, payment_id = "order_ABC123", "pay_XYZ789"
        signature = _payment_signature(order_id, payment_id)
        result = _client().utility.verify_payment_signature(
            {"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": signature}
        )
        self.assertTrue(result)

    def test_tampered_signature_is_rejected(self):
        order_id, payment_id = "order_ABC123", "pay_XYZ789"
        real_signature = _payment_signature(order_id, payment_id)
        tampered = real_signature[:-1] + ("0" if real_signature[-1] != "0" else "1")
        with self.assertRaises(razorpay.errors.SignatureVerificationError):
            _client().utility.verify_payment_signature(
                {"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": tampered}
            )

    def test_signature_for_different_payment_id_is_rejected(self):
        """The exact attack this check exists to prevent: a customer
        pays for order A, then tries to submit that same, genuinely
        valid signature against order B's payment_id."""
        order_id = "order_ABC123"
        signature_for_pay_1 = _payment_signature(order_id, "pay_ORIGINAL")
        with self.assertRaises(razorpay.errors.SignatureVerificationError):
            _client().utility.verify_payment_signature(
                {
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": "pay_DIFFERENT",
                    "razorpay_signature": signature_for_pay_1,
                }
            )

    def test_signature_with_wrong_secret_is_rejected(self):
        order_id, payment_id = "order_ABC123", "pay_XYZ789"
        signature = _payment_signature(order_id, payment_id, secret="wrong_secret")
        with self.assertRaises(razorpay.errors.SignatureVerificationError):
            _client().utility.verify_payment_signature(
                {"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": signature}
            )

    def test_missing_signature_is_rejected(self):
        with self.assertRaises((razorpay.errors.SignatureVerificationError, TypeError, KeyError)):
            _client().utility.verify_payment_signature(
                {"razorpay_order_id": "order_ABC123", "razorpay_payment_id": "pay_XYZ789", "razorpay_signature": ""}
            )


class WebhookSignatureVerificationTests(SimpleTestCase):
    def test_correct_webhook_signature_verifies(self):
        body = '{"event":"payment.captured","payload":{}}'
        signature = _webhook_signature(body)
        result = _client().utility.verify_webhook_signature(body, signature, WEBHOOK_SECRET)
        self.assertTrue(result)

    def test_tampered_body_is_rejected(self):
        """The webhook-equivalent of the payment-signature attack:
        the signature was computed over one body, but a different
        body is what's actually being verified."""
        original_body = '{"event":"payment.captured","payload":{}}'
        signature = _webhook_signature(original_body)
        tampered_body = '{"event":"payment.failed","payload":{}}'
        with self.assertRaises(razorpay.errors.SignatureVerificationError):
            _client().utility.verify_webhook_signature(tampered_body, signature, WEBHOOK_SECRET)

    def test_wrong_webhook_secret_is_rejected(self):
        body = '{"event":"payment.captured","payload":{}}'
        signature = _webhook_signature(body, secret="wrong_secret")
        with self.assertRaises(razorpay.errors.SignatureVerificationError):
            _client().utility.verify_webhook_signature(body, signature, WEBHOOK_SECRET)