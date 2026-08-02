import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.bookings import validators


class BusinessAndWebsiteNameValidationTests(TestCase):
    def test_valid_names_pass(self):
        validators.validate_business_name("Acme & Sons, Inc.")
        validators.validate_website_name("My Cool Site")

    def test_too_short_name_rejected(self):
        with self.assertRaises(ValidationError):
            validators.validate_business_name("A")

    def test_name_with_disallowed_characters_rejected(self):
        with self.assertRaises(ValidationError):
            validators.validate_business_name("<script>alert(1)</script>")


class DeliveryDateValidationTests(TestCase):
    def test_none_is_allowed(self):
        validators.validate_preferred_delivery_date(None)

    def test_date_too_soon_rejected(self):
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        with self.assertRaises(ValidationError):
            validators.validate_preferred_delivery_date(tomorrow)

    def test_date_far_enough_out_accepted(self):
        ok_date = timezone.localdate() + datetime.timedelta(days=14)
        validators.validate_preferred_delivery_date(ok_date)

    def test_date_too_far_in_future_rejected(self):
        too_far = timezone.localdate() + datetime.timedelta(days=1000)
        with self.assertRaises(ValidationError):
            validators.validate_preferred_delivery_date(too_far)


class ReferenceLinksValidationTests(TestCase):
    def test_valid_links_pass(self):
        validators.validate_reference_links([{"label": "Inspiration", "url": "https://example.com"}])

    def test_non_list_rejected(self):
        with self.assertRaises(ValidationError):
            validators.validate_reference_links("https://example.com")

    def test_invalid_url_rejected(self):
        with self.assertRaises(ValidationError):
            validators.validate_reference_links([{"url": "not-a-url"}])

    def test_too_many_links_rejected(self):
        links = [{"url": f"https://example.com/{i}"} for i in range(11)]
        with self.assertRaises(ValidationError):
            validators.validate_reference_links(links)


class AttachmentValidationTests(TestCase):
    def test_allowed_image_type_accepted(self):
        category = validators.validate_attachment("photo.jpg", 1024 * 1024)
        self.assertEqual(category, "IMAGE")

    def test_allowed_pdf_type_accepted(self):
        self.assertEqual(validators.validate_attachment("brief.pdf", 1024), "PDF")

    def test_disallowed_extension_rejected(self):
        with self.assertRaises(ValidationError):
            validators.validate_attachment("virus.exe", 1024)

    def test_oversized_file_rejected(self):
        too_big = 30 * 1024 * 1024  # over the 25MB default
        with self.assertRaises(ValidationError):
            validators.validate_attachment("large.pdf", too_big)

    def test_empty_file_rejected(self):
        with self.assertRaises(ValidationError):
            validators.validate_attachment("empty.pdf", 0)


class DuplicateSubmissionTests(TestCase):
    def test_no_key_is_a_no_op(self):
        validators.check_duplicate_submission(None)
        validators.check_duplicate_submission("")

    def test_unused_key_passes(self):
        validators.check_duplicate_submission("brand-new-key")