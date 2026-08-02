from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tokens import email_verification_token, encode_uid

User = get_user_model()

VALID_PASSWORD = "Str0ng!Passw0rd"


class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="janedoe",
            email="jane@example.com",
            password=VALID_PASSWORD,
            role="CUSTOMER",
            is_active=False,
            is_email_verified=False,
        )

    def test_valid_token_verifies_and_activates_account(self):
        uid = encode_uid(self.user.pk)
        token = email_verification_token.make_token(self.user)

        response = self.client.post(
            reverse("accounts:verify-email"), {"uid": uid, "token": token}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        self.assertTrue(self.user.is_active)

    def test_invalid_token_is_rejected(self):
        uid = encode_uid(self.user.pk)
        response = self.client.post(
            reverse("accounts:verify-email"),
            {"uid": uid, "token": "not-a-real-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_token_is_single_use(self):
        uid = encode_uid(self.user.pk)
        token = email_verification_token.make_token(self.user)

        first = self.client.post(
            reverse("accounts:verify-email"), {"uid": uid, "token": token}, format="json"
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(
            reverse("accounts:verify-email"), {"uid": uid, "token": token}, format="json"
        )
        # Already verified — a friendly 200, not an error, but it must
        # not be treated as a fresh verification.
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertIn("already verified", second.data["detail"].lower())

    def test_resend_verification_sends_email_for_unverified_user(self):
        response = self.client.post(
            reverse("accounts:resend-verification"), {"email": "jane@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_verification_gives_generic_response_for_unknown_email(self):
        response = self.client.post(
            reverse("accounts:resend-verification"),
            {"email": "nobody@example.com"},
            format="json",
        )
        # Same 200 + generic message as a real account — must not leak
        # whether the address is registered.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)