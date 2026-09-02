"""
PaymentOrderService tests. Razorpay's own API (order.create) is
mocked — a real call would need live network access and real
credentials this test suite doesn't have and shouldn't depend on;
signature verification itself (a pure function, no network) is tested
for real, unmocked, in test_signature_verification.py.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.bookings.services import BookingService, ProjectLifecycleService
from apps.catalog.models import Package, ServiceCategory, WebsiteCategory
from apps.configuration.models import PaymentConfiguration
from apps.payments.models import Payment, PaymentOrder, ProjectPriceSnapshot
from apps.payments.services import PaymentOrderService

User = get_user_model()
VALID_PASSWORD = "Str0ng!Passw0rd"


class PaymentFixtureMixin:
    def setUp(self):
        self.customer = User.objects.create_user(
            username="pay_cust", email="pay_cust@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.other_customer = User.objects.create_user(
            username="pay_cust2", email="pay_cust2@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.developer = User.objects.create_user(
            username="pay_dev", email="pay_dev@example.com", password=VALID_PASSWORD,
            role="DEVELOPER", is_active=True, is_email_verified=True,
        )
        self.admin = User.objects.create_user(
            username="pay_admin", email="pay_admin@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )

        self.category = ServiceCategory.objects.create(name="Pay Service", slug="pay-service")
        self.website_category = WebsiteCategory.objects.create(name="Pay Website Cat", slug="pay-website-cat")
        self.package = Package.objects.create(
            service_category=self.category, tier="BASIC", name="Pay Package", slug="pay-package",
            description="x", starting_price=Decimal("1000.00"), delivery_days=10,
            revision_count=2, support_duration_days=30, status=Package.Status.PUBLISHED,
        )

        config = PaymentConfiguration.load()
        config.is_enabled = True
        config.razorpay_key_id = "rzp_test_dummy_key_id"
        config.razorpay_key_secret = "dummy_key_secret"
        config.razorpay_webhook_secret = "dummy_webhook_secret"
        config.default_currency = "INR"
        config.save()
        self.payment_config = config

    def _draft_booking(self, customer=None):
        return BookingService.create_booking(
            customer=customer or self.customer, package=self.package, website_category=self.website_category,
            website_name="Pay Test Site", business_name="Pay Test Co", business_type="STARTUP", description="x",
        )

    def _accepted_booking(self, customer=None, developer=None):
        booking = self._draft_booking(customer=customer)
        booking = BookingService.submit(booking, actor=booking.customer)
        return ProjectLifecycleService.accept_project(booking.id, developer=developer or self.developer)

    @staticmethod
    def _mock_razorpay_client(order_create_return=None):
        client = MagicMock()
        client.order.create.return_value = order_create_return or {"id": "order_MOCKED123", "status": "created"}
        return client


class OrderCreationTests(PaymentFixtureMixin, TestCase):
    def test_create_advance_order_for_accepted_booking(self):
        booking = self._accepted_booking()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=self._mock_razorpay_client()):
            order = PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)
        self.assertEqual(order.razorpay_order_id, "order_MOCKED123")
        self.assertEqual(order.amount, Decimal("500.00"))  # 50% of 1000.00
        self.assertEqual(order.status, PaymentOrder.Status.CREATED)

    def test_order_amount_is_half_of_snapshot_price(self):
        booking = self._accepted_booking()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=self._mock_razorpay_client()):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)
        payment = Payment.objects.get(booking=booking, phase=Payment.Phase.ADVANCE_PAYMENT)
        self.assertEqual(payment.amount, Decimal("500.00"))

    def test_creates_price_snapshot_on_first_order(self):
        booking = self._accepted_booking()
        self.assertFalse(ProjectPriceSnapshot.objects.filter(booking=booking).exists())
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=self._mock_razorpay_client()):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)
        self.assertTrue(ProjectPriceSnapshot.objects.filter(booking=booking).exists())

    def test_snapshot_price_survives_later_package_price_change(self):
        booking = self._accepted_booking()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=self._mock_razorpay_client()):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)

        self.package.starting_price = Decimal("5000.00")
        self.package.save()

        payment = Payment.objects.get(booking=booking, phase=Payment.Phase.ADVANCE_PAYMENT)
        self.assertEqual(payment.amount, Decimal("500.00"))  # unchanged — snapshot-derived, not re-read from package

    def test_cannot_create_advance_order_before_acceptance(self):
        booking = self._draft_booking()  # still draft, never accepted
        with self.assertRaises(ValidationError):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)

    def test_cannot_create_final_order_before_advance_captured(self):
        booking = self._accepted_booking()
        with self.assertRaises(ValidationError):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.FINAL_PAYMENT, customer=self.customer)

    def test_other_customer_cannot_create_order(self):
        booking = self._accepted_booking()
        with self.assertRaises(ValidationError):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.other_customer)

    def test_cannot_create_order_when_payments_disabled(self):
        self.payment_config.is_enabled = False
        self.payment_config.save()
        booking = self._accepted_booking()
        with self.assertRaises(ValidationError):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)

    def test_duplicate_order_request_reuses_active_order(self):
        """Two rapid create-order calls (duplicate click) while the
        first order is still active must not create two Razorpay
        orders."""
        booking = self._accepted_booking()
        client = self._mock_razorpay_client()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            first = PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)
            second = PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)

        self.assertEqual(first.id, second.id)
        self.assertEqual(client.order.create.call_count, 1)

    def test_cannot_create_order_for_already_captured_payment(self):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.CAPTURED,
        )
        with self.assertRaises(ValidationError):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)

    def test_retry_after_failure_creates_new_order_on_same_payment(self):
        booking = self._accepted_booking()
        client = self._mock_razorpay_client()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            first = PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)

        payment = first.payment
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status"])
        first.status = PaymentOrder.Status.CANCELLED
        first.save(update_fields=["status"])

        client2 = self._mock_razorpay_client(order_create_return={"id": "order_RETRY456", "status": "created"})
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client2):
            second = PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(second.payment_id, payment.id)  # same logical Payment, not a duplicate

    def test_each_order_gets_a_unique_receipt(self):
        booking = self._accepted_booking()
        client = self._mock_razorpay_client()
        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)
        receipt = client.order.create.call_args.kwargs["data"]["receipt"]
        self.assertLessEqual(len(receipt), 40)  # Razorpay's own limit