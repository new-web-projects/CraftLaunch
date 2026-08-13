from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.configuration.models import StorageConfiguration

User = get_user_model()
VALID_PASSWORD = "Str0ng!Passw0rd"


class ConfigurationPermissionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )
        self.customer = User.objects.create_user(
            username="customer", email="customer@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.developer = User.objects.create_user(
            username="developer", email="developer@example.com", password=VALID_PASSWORD,
            role="DEVELOPER", is_active=True, is_email_verified=True,
        )

    def tearDown(self):
        # See test_email_integration.py's tearDown docstring — the
        # cache isn't rolled back with the DB transaction between
        # tests, so anything that saved a configuration row here has
        # to clear it explicitly.
        cache.clear()

    def test_public_endpoint_reachable_without_authentication(self):
        response = self.client.get(reverse("configuration:public"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("site", response.data)
        self.assertIn("seo", response.data)
        self.assertIn("feature_flags", response.data)
        self.assertEqual(response.data["site"]["website_name"], "CraftLaunch")

    def test_public_endpoint_never_exposes_secret_categories(self):
        response = self.client.get(reverse("configuration:public"))
        payload_str = str(response.data)
        for leaked_key in ("smtp_password", "razorpay_key_secret", "s3_secret_access_key"):
            self.assertNotIn(leaked_key, payload_str)

    def test_anonymous_cannot_read_admin_settings(self):
        for url_name in ["site", "seo", "storage", "email", "payment", "feature-flags"]:
            response = self.client.get(reverse(f"configuration:{url_name}"))
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, url_name)

    def test_customer_cannot_read_admin_settings(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("configuration:site"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_developer_cannot_read_admin_settings(self):
        self.client.force_authenticate(self.developer)
        response = self.client.get(reverse("configuration:site"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_write_admin_settings(self):
        self.client.force_authenticate(self.customer)
        response = self.client.patch(reverse("configuration:site"), {"website_name": "Hacked"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_read_and_write_site_settings(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            reverse("configuration:site"), {"website_name": "Renamed Co", "tagline": "New tagline"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["website_name"], "Renamed Co")

        get_response = self.client.get(reverse("configuration:site"))
        self.assertEqual(get_response.data["website_name"], "Renamed Co")
        self.assertEqual(get_response.data["tagline"], "New tagline")

    def test_website_name_update_is_visible_immediately_through_the_public_endpoint(self):
        # This is the spec's "Website Name updates instantly" check,
        # exercised end-to-end through the actual cached read path
        # rather than asserted against the model directly.
        self.client.force_authenticate(self.admin)
        self.client.patch(reverse("configuration:site"), {"website_name": "Instant Co"})

        public_response = self.client.get(reverse("configuration:public"))
        self.assertEqual(public_response.data["site"]["website_name"], "Instant Co")


class SecretFieldMaskingTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin2", email="admin2@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )
        self.client.force_authenticate(self.admin)

    def tearDown(self):
        cache.clear()

    def test_storage_secret_is_write_only(self):
        self.client.patch(
            reverse("configuration:storage"),
            {"active_provider": "S3", "s3_secret_access_key": "AKIA-real-secret-value"},
        )
        response = self.client.get(reverse("configuration:storage"))
        self.assertNotIn("AKIA-real-secret-value", str(response.data))
        self.assertNotIn("s3_secret_access_key", response.data)
        self.assertTrue(response.data["s3_secret_access_key_is_set"])

    def test_blank_secret_on_patch_does_not_clear_existing_value(self):
        self.client.patch(reverse("configuration:storage"), {"s3_secret_access_key": "original-secret"})
        # Admin re-saves the bucket name; the secret field is blank in
        # the form because write_only fields never come back on GET.
        self.client.patch(reverse("configuration:storage"), {"s3_bucket_name": "my-bucket"})

        stored = StorageConfiguration.objects.get(pk=1)
        self.assertEqual(stored.s3_secret_access_key, "original-secret")
        self.assertEqual(stored.s3_bucket_name, "my-bucket")

    def test_payment_secrets_are_write_only_and_default_disabled(self):
        response = self.client.get(reverse("configuration:payment"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_enabled"])
        self.assertFalse(response.data["razorpay_key_secret_is_set"])

        self.client.patch(
            reverse("configuration:payment"),
            {"razorpay_key_id": "rzp_test_abc", "razorpay_key_secret": "secret_value"},
        )
        response = self.client.get(reverse("configuration:payment"))
        self.assertNotIn("secret_value", str(response.data))
        self.assertTrue(response.data["razorpay_key_secret_is_set"])
        # Saving credentials must never silently flip payments on.
        self.assertFalse(response.data["is_enabled"])