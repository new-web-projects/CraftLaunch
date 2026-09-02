from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import Payment, PaymentOrder

from .test_order_creation import PaymentFixtureMixin


class OrderCreationAPITests(PaymentFixtureMixin, APITestCase):
    def test_unauthenticated_request_is_rejected(self):
        booking = self._accepted_booking()
        response = self.client.post(reverse("payments:advance-order-create", args=[booking.id]))
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_developer_cannot_create_payment_order(self):
        """Order creation is a customer action — a developer, even one
        assigned to the project, may not initiate a payment on the
        customer's behalf."""
        booking = self._accepted_booking()
        self.client.force_authenticate(self.developer)
        response = self.client.post(reverse("payments:advance-order-create", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_customer_gets_404_not_leaked_403(self):
        """Same for_user()-scoping convention as every other booking
        sub-resource in this codebase — a stranger's booking ID
        doesn't even resolve for them."""
        booking = self._accepted_booking()
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(reverse("payments:advance-order-create", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_order_creation_response_shape(self):
        booking = self._accepted_booking()
        client = MagicMock()
        client.order.create.return_value = {"id": "order_API1", "status": "created"}
        self.client.force_authenticate(self.customer)
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            response = self.client.post(reverse("payments:advance-order-create", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["razorpay_order_id"], "order_API1")
        self.assertEqual(Decimal(response.data["amount"]), Decimal("500.00"))
        self.assertIn("razorpay_key_id", response.data)

    def test_key_secret_never_appears_in_response(self):
        booking = self._accepted_booking()
        client = MagicMock()
        client.order.create.return_value = {"id": "order_API2", "status": "created"}
        self.client.force_authenticate(self.customer)
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            response = self.client.post(reverse("payments:advance-order-create", args=[booking.id]))
        body_text = str(response.data)
        self.assertNotIn(self.payment_config.razorpay_key_secret, body_text)
        self.assertNotIn(self.payment_config.razorpay_webhook_secret, body_text)
        self.assertNotIn("razorpay_key_secret", body_text)
        self.assertNotIn("webhook_secret", body_text)

    def test_final_order_before_advance_captured_returns_400(self):
        booking = self._accepted_booking()
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("payments:final-order-create", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PaymentSummaryAndHistoryAPITests(PaymentFixtureMixin, APITestCase):
    def test_summary_visible_to_owner(self):
        booking = self._accepted_booking()
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("payments:summary", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["total_amount"]), Decimal("1000.00"))

    def test_summary_visible_to_assigned_developer(self):
        booking = self._accepted_booking()
        self.client.force_authenticate(self.developer)
        response = self.client.get(reverse("payments:summary", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_summary_not_visible_to_stranger(self):
        booking = self._accepted_booking()
        self.client.force_authenticate(self.other_customer)
        response = self.client.get(reverse("payments:summary", args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_history_only_shows_own_payments(self):
        my_booking = self._accepted_booking(customer=self.customer)
        other_booking = self._accepted_booking(customer=self.other_customer)
        Payment.objects.create(
            booking=my_booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        Payment.objects.create(
            booking=other_booking, customer=self.other_customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("payments:history"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking_ids = {row["booking_id"] for row in response.data["results"]}
        self.assertEqual(booking_ids, {str(my_booking.id)})

    def test_developer_cannot_access_payment_history_endpoint(self):
        """PaymentHistoryView is customer-only — a developer's own
        equivalent visibility is the per-booking summary/status
        endpoints, not a cross-booking financial history."""
        self.client.force_authenticate(self.developer)
        response = self.client.get(reverse("payments:history"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminPaymentListAPITests(PaymentFixtureMixin, APITestCase):
    def test_admin_can_list_all_payments(self):
        b1 = self._accepted_booking(customer=self.customer)
        b2 = self._accepted_booking(customer=self.other_customer)
        Payment.objects.create(
            booking=b1, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        Payment.objects.create(
            booking=b2, customer=self.other_customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.FAILED,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("payments:admin-payment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_admin_can_filter_by_status(self):
        booking = self._accepted_booking()
        Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.FAILED,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("payments:admin-payment-list"), {"status": "FAILED"})
        self.assertEqual(response.data["count"], 1)
        response = self.client.get(reverse("payments:admin-payment-list"), {"status": "CAPTURED"})
        self.assertEqual(response.data["count"], 0)

    def test_customer_cannot_access_admin_payment_list(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("payments:admin-payment-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_developer_cannot_access_admin_payment_list(self):
        self.client.force_authenticate(self.developer)
        response = self.client.get(reverse("payments:admin-payment-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WebhookAPITests(PaymentFixtureMixin, APITestCase):
    def test_webhook_endpoint_requires_no_authentication(self):
        """Razorpay's servers carry no session/JWT — the endpoint
        itself is reachable without auth (the signature is the auth);
        an invalid/missing signature is still rejected, just not by
        DRF's normal authentication layer."""
        response = self.client.post(
            reverse("payments:webhook"), data="{}", content_type="application/json"
        )
        # No auth error (401) — reaches the view and fails on
        # signature verification (400) instead.
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_webhook_with_valid_signature_returns_200(self):
        import hashlib
        import hmac
        import json

        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.ORDER_CREATED,
        )
        PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_WEBHOOKAPI", amount=Decimal("500.00"),
            amount_paise=50000, currency="INR", receipt="api-wh-receipt", status=PaymentOrder.Status.CREATED,
        )
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_WEBHOOKAPI1", "order_id": "order_WEBHOOKAPI",
                        "amount": 50000, "currency": "INR", "status": "captured", "method": "card",
                    }
                }
            },
        }
        body = json.dumps(payload)
        signature = hmac.new(
            self.payment_config.razorpay_webhook_secret.encode(), body.encode(), hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            reverse("payments:webhook"), data=body, content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature, HTTP_X_RAZORPAY_EVENT_ID="evt_api_1",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)