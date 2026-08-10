from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.services import BookingService
from apps.catalog.models import Package, ServiceCategory, WebsiteCategory

User = get_user_model()
VALID_PASSWORD = "Str0ng!Passw0rd"


class BookingPermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.stranger = User.objects.create_user(
            username="stranger", email="stranger@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.assigned_dev = User.objects.create_user(
            username="assigneddev", email="assigneddev@example.com", password=VALID_PASSWORD,
            role="DEVELOPER", is_active=True, is_email_verified=True,
        )
        self.unassigned_dev = User.objects.create_user(
            username="unassigneddev", email="unassigneddev@example.com", password=VALID_PASSWORD,
            role="DEVELOPER", is_active=True, is_email_verified=True,
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )

        category = ServiceCategory.objects.create(name="Perm Test Service", slug="perm-test-service")
        website_category = WebsiteCategory.objects.create(name="Perm Test Website Cat", slug="perm-test-website-cat")
        package = Package.objects.create(
            service_category=category, tier="BASIC", name="Perm Test Package",
            slug="perm-test-package", description="x", starting_price="500.00",
            delivery_days=10, revision_count=2, support_duration_days=30,
            status=Package.Status.PUBLISHED,
        )
        self.booking = BookingService.create_booking(
            customer=self.owner, package=package, website_category=website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP", description="x",
        )
        BookingService.assign_developer(self.booking, self.assigned_dev, assigned_by=self.admin)

    def _detail_url(self):
        return reverse("bookings:detail", args=[self.booking.id])

    def _timeline_url(self):
        return reverse("bookings:timeline", args=[self.booking.id])

    def test_owner_can_view(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assigned_developer_can_view(self):
        self.client.force_authenticate(self.assigned_dev)
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_view(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unrelated_customer_cannot_view(self):
        self.client.force_authenticate(self.stranger)
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unassigned_developer_cannot_view(self):
        self.client.force_authenticate(self.unassigned_dev)
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assigned_developer_cannot_edit(self):
        self.client.force_authenticate(self.assigned_dev)
        response = self.client.patch(self._detail_url(), {"website_name": "Hacked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_edit(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(self._detail_url(), {"website_name": "Renamed Shop"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_internal_notes_hidden_from_customer(self):
        BookingService.add_note(self.booking, author=self.admin, content="Internal only", is_internal=True)
        BookingService.add_note(self.booking, author=self.owner, content="Visible to customer", is_internal=False)

        self.client.force_authenticate(self.owner)
        response = self.client.get(self._detail_url())
        note_contents = [n["content"] for n in response.data["notes"]]
        self.assertIn("Visible to customer", note_contents)
        self.assertNotIn("Internal only", note_contents)

    def test_internal_notes_visible_to_admin(self):
        BookingService.add_note(self.booking, author=self.admin, content="Internal only", is_internal=True)

        self.client.force_authenticate(self.admin)
        response = self.client.get(self._detail_url())
        note_contents = [n["content"] for n in response.data["notes"]]
        self.assertIn("Internal only", note_contents)

    # Regression coverage for BookingTimelineView.get_queryset(): it
    # used to look bookings up via the unscoped `Booking.objects`
    # manager instead of `.for_user(...)`, so a non-participant's
    # request would find the row and only get blocked at the
    # object-permission check — a 403 that confirms the booking
    # exists, instead of the 404 every other by-ID lookup on this
    # resource gives. Mirrors the equivalent detail-view tests above.
    def test_owner_can_view_timeline(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assigned_developer_can_view_timeline(self):
        self.client.force_authenticate(self.assigned_dev)
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_view_timeline(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unrelated_customer_cannot_view_timeline(self):
        self.client.force_authenticate(self.stranger)
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unassigned_developer_cannot_view_timeline(self):
        self.client.force_authenticate(self.unassigned_dev)
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)