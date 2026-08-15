"""
These mock every third-party SDK/network call (boto3, cloudinary,
urllib, smtplib) rather than reaching real AWS/Cloudinary/Razorpay
APIs — standard practice for a test suite (you don't want CI's pass/
fail depending on a third party's uptime), and also a hard requirement
here: this sandbox's network egress is allowlisted to package
registries and GitHub, not to these providers' actual endpoints. What
these tests verify is that TestStorageConnectionView / TestEmailConnectionView /
TestPaymentConnectionView call the right SDK method with the right
arguments and correctly translate success/failure into the response
shape and the last_tested_at/last_test_success fields — not that a
real AWS account's credentials are actually valid.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.configuration.models import EmailConfiguration, PaymentConfiguration, StorageConfiguration

User = get_user_model()
VALID_PASSWORD = "Str0ng!Passw0rd"


class TestConnectionViewsTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin3", email="admin3@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )
        self.client.force_authenticate(self.admin)

    # ---- Storage ------------------------------------------------------

    def test_local_provider_succeeds_without_any_network_call(self):
        config = StorageConfiguration.load()
        config.active_provider = "LOCAL"
        config.save()

        response = self.client.post(reverse("configuration:storage-test"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_s3_missing_credentials_fails_without_a_network_call(self):
        config = StorageConfiguration.load()
        config.active_provider = "S3"
        config.save()

        response = self.client.post(reverse("configuration:storage-test"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("required", response.data["detail"])

    @patch("boto3.client")
    def test_s3_success_updates_last_test_fields(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        config = StorageConfiguration.load()
        config.active_provider = "S3"
        config.s3_access_key_id = "AKIAFAKE"
        config.s3_secret_access_key = "fakesecret"
        config.s3_bucket_name = "my-bucket"
        config.save()

        response = self.client.post(reverse("configuration:storage-test"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_s3.head_bucket.assert_called_once_with(Bucket="my-bucket")

        reloaded = StorageConfiguration.objects.get(pk=1)
        self.assertTrue(reloaded.last_test_success)
        self.assertIsNotNone(reloaded.last_tested_at)

    @patch("boto3.client")
    def test_s3_failure_is_reported_not_a_500(self, mock_boto_client):
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadBucket"
        )
        mock_boto_client.return_value = mock_s3

        config = StorageConfiguration.load()
        config.active_provider = "S3"
        config.s3_access_key_id = "AKIAFAKE"
        config.s3_secret_access_key = "wrongsecret"
        config.s3_bucket_name = "my-bucket"
        config.save()

        response = self.client.post(reverse("configuration:storage-test"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        reloaded = StorageConfiguration.objects.get(pk=1)
        self.assertFalse(reloaded.last_test_success)

    @patch("cloudinary.api.ping")
    def test_cloudinary_success(self, mock_ping):
        mock_ping.return_value = {"status": "ok"}

        config = StorageConfiguration.load()
        config.active_provider = "CLOUDINARY"
        config.cloudinary_cloud_name = "demo"
        config.cloudinary_api_key = "123456"
        config.cloudinary_api_secret = "fakesecret"
        config.save()

        response = self.client.post(reverse("configuration:storage-test"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    # ---- Email ----------------------------------------------------------

    def test_email_missing_host_fails_without_a_network_call(self):
        response = self.client.post(reverse("configuration:email-test"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("required", response.data["detail"])

    @patch("django.core.mail.get_connection")
    def test_email_connection_success(self, mock_get_connection):
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        config = EmailConfiguration.load()
        config.smtp_host = "smtp.example.com"
        config.smtp_port = 587
        config.save()

        response = self.client.post(reverse("configuration:email-test"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_connection.open.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch("django.core.mail.get_connection")
    def test_email_connection_failure_is_reported_not_a_500(self, mock_get_connection):
        mock_connection = MagicMock()
        mock_connection.open.side_effect = ConnectionRefusedError("refused")
        mock_get_connection.return_value = mock_connection

        config = EmailConfiguration.load()
        config.smtp_host = "smtp.example.com"
        config.save()

        response = self.client.post(reverse("configuration:email-test"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    @patch("django.core.mail.send_mail")
    @patch("django.core.mail.get_connection")
    def test_send_test_email_flag_actually_sends(self, mock_get_connection, mock_send_mail):
        mock_get_connection.return_value = MagicMock()

        config = EmailConfiguration.load()
        config.smtp_host = "smtp.example.com"
        config.save()

        response = self.client.post(
            reverse("configuration:email-test"), {"send_test_email": True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args.kwargs
        self.assertEqual(call_kwargs["recipient_list"], [self.admin.email])

    # ---- Payment ----------------------------------------------------------

    def test_payment_missing_credentials_fails_without_a_network_call(self):
        response = self.client.post(reverse("configuration:payment-test"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("required", response.data["detail"])

    @patch("urllib.request.urlopen")
    def test_payment_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        config = PaymentConfiguration.load()
        config.razorpay_key_id = "rzp_test_fake"
        config.razorpay_key_secret = "fakesecret"
        config.save()

        response = self.client.post(reverse("configuration:payment-test"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    @patch("urllib.request.urlopen")
    def test_payment_401_is_reported_clearly(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.razorpay.com/v1/payments?count=1", 401, "Unauthorized", {}, None
        )

        config = PaymentConfiguration.load()
        config.razorpay_key_id = "rzp_test_fake"
        config.razorpay_key_secret = "wrongsecret"
        config.save()

        response = self.client.post(reverse("configuration:payment-test"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("401", response.data["detail"])

    def test_payment_test_never_charges_or_creates_anything(self):
        # Sanity check on the implementation choice itself: the only
        # network call payment testing makes is a GET, never a POST —
        # this is a credential check, not a payment operation.
        import inspect

        from apps.configuration.views import TestPaymentConnectionView

        source = inspect.getsource(TestPaymentConnectionView._test)
        self.assertNotIn('"POST"', source)
        self.assertNotIn("method=\"POST\"", source)
