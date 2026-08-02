import datetime

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking, BookingRequirement, BookingTimeline, CustomerRequirement, ProjectStatus
from apps.bookings.services import BookingService
from apps.catalog.models import Package, ServiceCategory, WebsiteCategory, WebsiteFeature, WebsiteType

User = get_user_model()
VALID_PASSWORD = "Str0ng!Passw0rd"


class BookingTestFixtureMixin:
    def setUp(self):
        self.customer = User.objects.create_user(
            username="cust", email="cust@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.other_customer = User.objects.create_user(
            username="cust2", email="cust2@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.category = ServiceCategory.objects.create(name="Booking Test Service", slug="booking-test-service")
        self.website_category = WebsiteCategory.objects.create(name="Booking Test Website Cat", slug="booking-test-website-cat")
        self.website_type = WebsiteType.objects.create(name="Booking Test Website Type", slug="booking-test-website-type")
        self.feature = WebsiteFeature.objects.create(name="Booking Test Feature", slug="booking-test-feature")
        self.package = Package.objects.create(
            service_category=self.category, tier="BASIC", name="Booking Test Package",
            slug="booking-test-package", description="x", starting_price="500.00",
            delivery_days=10, revision_count=2, support_duration_days=30,
            status=Package.Status.PUBLISHED,
        )
        self.future_date = timezone.localdate() + datetime.timedelta(days=14)


class BookingServiceCreateTests(BookingTestFixtureMixin, APITestCase):
    """Booking creation works — service layer."""

    def test_create_booking_sets_default_status(self):
        booking = BookingService.create_booking(
            customer=self.customer, package=self.package, website_category=self.website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP",
            description="Need a shop.", preferred_delivery_date=self.future_date,
        )
        self.assertEqual(booking.status.code, "draft")
        self.assertEqual(booking.customer, self.customer)

    def test_create_booking_logs_timeline_event(self):
        booking = BookingService.create_booking(
            customer=self.customer, package=self.package, website_category=self.website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP",
            description="Need a shop.",
        )
        events = BookingTimeline.objects.filter(booking=booking)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().event_type, BookingTimeline.EventType.BOOKING_CREATED)

    def test_create_booking_with_required_features(self):
        booking = BookingService.create_booking(
            customer=self.customer, package=self.package, website_category=self.website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP",
            description="Need a shop.", required_feature_ids=[self.feature.id],
        )
        self.assertTrue(
            BookingRequirement.objects.filter(booking=booking, website_feature=self.feature).exists()
        )

    def test_create_booking_with_custom_requirements(self):
        booking = BookingService.create_booking(
            customer=self.customer, package=self.package, website_category=self.website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP",
            description="Need a shop.",
            custom_requirements=[{"title": "CRM integration", "description": "Connect to our CRM"}],
        )
        self.assertEqual(CustomerRequirement.objects.filter(booking=booking).count(), 1)

    def test_duplicate_idempotency_key_rejected(self):
        BookingService.create_booking(
            customer=self.customer, package=self.package, website_category=self.website_category,
            website_name="First", business_name="Acme Co", business_type="STARTUP",
            description="x", idempotency_key="abc-123",
        )
        with self.assertRaises(Exception):
            BookingService.create_booking(
                customer=self.customer, package=self.package, website_category=self.website_category,
                website_name="Second", business_name="Acme Co", business_type="STARTUP",
                description="x", idempotency_key="abc-123",
            )
        self.assertEqual(Booking.objects.filter(idempotency_key="abc-123").count(), 1)


class BookingCreateAPITests(BookingTestFixtureMixin, APITestCase):
    """Booking creation works — through the API."""

    def _payload(self, **overrides):
        payload = {
            "package": self.package.id,
            "website_category": self.website_category.id,
            "website_name": "My Shop",
            "business_name": "Acme Co",
            "business_type": "STARTUP",
            "description": "Need an online shop.",
            "preferred_delivery_date": str(self.future_date),
        }
        payload.update(overrides)
        return payload

    def test_customer_can_create_booking(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("bookings:list-create"), self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["status"]["code"], "draft")

    def test_developer_cannot_create_booking(self):
        developer = User.objects.create_user(
            username="dev", email="dev@example.com", password=VALID_PASSWORD,
            role="DEVELOPER", is_active=True, is_email_verified=True,
        )
        self.client.force_authenticate(developer)
        response = self.client.post(reverse("bookings:list-create"), self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_booking(self):
        response = self.client.post(reverse("bookings:list-create"), self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_sees_only_own_bookings_in_list(self):
        self.client.force_authenticate(self.customer)
        self.client.post(reverse("bookings:list-create"), self._payload(), format="json")

        self.client.force_authenticate(self.other_customer)
        response = self.client.get(reverse("bookings:list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_cannot_book_an_unpublished_package(self):
        draft_package = Package.objects.create(
            service_category=self.category, tier="STANDARD", name="Draft Pkg",
            slug="draft-pkg-booking-test", description="x", starting_price="800.00",
            delivery_days=10, revision_count=2, support_duration_days=30,
        )
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("bookings:list-create"), self._payload(package=draft_package.id), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BookingStatusTransitionTests(BookingTestFixtureMixin, APITestCase):
    def test_cancel_moves_to_cancelled_status(self):
        booking = BookingService.create_booking(
            customer=self.customer, package=self.package, website_category=self.website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP", description="x",
        )
        BookingService.cancel(booking, actor=self.customer, reason="Changed my mind")
        booking.refresh_from_db()
        self.assertEqual(booking.status.code, "cancelled")

    def test_cannot_cancel_a_terminal_booking_again(self):
        booking = BookingService.create_booking(
            customer=self.customer, package=self.package, website_category=self.website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP", description="x",
        )
        BookingService.cancel(booking, actor=self.customer)
        booking.refresh_from_db()
        with self.assertRaises(Exception):
            BookingService.cancel(booking, actor=self.customer)

    def test_cancel_via_api(self):
        self.client.force_authenticate(self.customer)
        create = self.client.post(
            reverse("bookings:list-create"),
            {
                "package": self.package.id, "website_category": self.website_category.id,
                "website_name": "My Shop", "business_name": "Acme Co",
                "business_type": "STARTUP", "description": "x",
            },
            format="json",
        )
        booking_id = create.data["id"]
        response = self.client.post(reverse("bookings:cancel", args=[booking_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"]["code"], "cancelled")