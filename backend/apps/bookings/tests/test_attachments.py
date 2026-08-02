import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import ProjectAttachment
from apps.bookings.services import BookingService
from apps.catalog.models import Package, ServiceCategory, WebsiteCategory

User = get_user_model()
VALID_PASSWORD = "Str0ng!Passw0rd"


class AttachmentTests(APITestCase):
    """Attachment upload structure works."""

    def setUp(self):
        self.customer = User.objects.create_user(
            username="cust", email="cust@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.other_customer = User.objects.create_user(
            username="cust2", email="cust2@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        category = ServiceCategory.objects.create(name="Attachment Test Service", slug="attachment-test-service")
        website_category = WebsiteCategory.objects.create(name="Attachment Test Website Cat", slug="attachment-test-website-cat")
        package = Package.objects.create(
            service_category=category, tier="BASIC", name="Attachment Test Package",
            slug="attachment-test-package", description="x", starting_price="500.00",
            delivery_days=10, revision_count=2, support_duration_days=30,
            status=Package.Status.PUBLISHED,
        )
        self.booking = BookingService.create_booking(
            customer=self.customer, package=package, website_category=website_category,
            website_name="My Shop", business_name="Acme Co", business_type="STARTUP", description="x",
        )

    def test_owner_can_upload_attachment(self):
        self.client.force_authenticate(self.customer)
        upload = SimpleUploadedFile("brief.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf")
        response = self.client.post(
            reverse("bookings:attachment-upload", args=[self.booking.id]), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["file_category"], "PDF")
        self.assertEqual(response.data["original_filename"], "brief.pdf")

        attachment = ProjectAttachment.objects.get(booking=self.booking)
        self.assertEqual(attachment.storage_provider, "LOCAL")
        self.assertEqual(attachment.uploaded_by, self.customer)

    def test_non_participant_cannot_upload(self):
        self.client.force_authenticate(self.other_customer)
        upload = SimpleUploadedFile("brief.pdf", b"content", content_type="application/pdf")
        response = self.client.post(
            reverse("bookings:attachment-upload", args=[self.booking.id]), {"file": upload}, format="multipart"
        )
        # Not 403 — the booking isn't in this user's scoped queryset at
        # all, so it 404s rather than confirming a private booking's
        # existence to someone with no relationship to it.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_disallowed_file_type_rejected(self):
        self.client.force_authenticate(self.customer)
        upload = SimpleUploadedFile("malware.exe", b"content", content_type="application/octet-stream")
        response = self.client.post(
            reverse("bookings:attachment-upload", args=[self.booking.id]), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_logs_timeline_event(self):
        self.client.force_authenticate(self.customer)
        upload = SimpleUploadedFile("photo.jpg", b"fake image bytes", content_type="image/jpeg")
        self.client.post(
            reverse("bookings:attachment-upload", args=[self.booking.id]), {"file": upload}, format="multipart"
        )
        self.assertTrue(
            self.booking.timeline_events.filter(event_type="FILE_UPLOADED").exists()
        )

    def test_owner_can_delete_attachment(self):
        self.client.force_authenticate(self.customer)
        upload = SimpleUploadedFile("notes.txt", b"some notes", content_type="text/plain")
        create = self.client.post(
            reverse("bookings:attachment-upload", args=[self.booking.id]), {"file": upload}, format="multipart"
        )
        attachment_id = create.data["id"]

        response = self.client.delete(
            reverse("bookings:attachment-delete", args=[self.booking.id, attachment_id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Soft-deleted — gone from the default manager, not from the table.
        self.assertFalse(ProjectAttachment.objects.filter(id=attachment_id).exists())
        self.assertTrue(ProjectAttachment.all_objects.filter(id=attachment_id).exists())