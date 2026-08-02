from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tokens import encode_uid, password_reset_token

User = get_user_model()

VALID_PASSWORD = "Str0ng!Passw0rd"
NEW_PASSWORD = "N3wPassw0rd!"


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="janedoe",
            email="jane@example.com",
            password=VALID_PASSWORD,
            role="CUSTOMER",
            is_active=True,
            is_email_verified=True,
        )

    def test_forgot_password_sends_email_for_existing_user(self):
        response = self.client.post(
            reverse("accounts:forgot-password"), {"email": "jane@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset", mail.outbox[0].subject.lower())

    def test_forgot_password_gives_generic_response_for_unknown_email(self):
        response = self.client.post(
            reverse("accounts:forgot-password"), {"email": "nobody@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_password_with_valid_token_changes_password(self):
        uid = encode_uid(self.user.pk)
        token = password_reset_token.make_token(self.user)

        response = self.client.post(
            reverse("accounts:reset-password"),
            {"uid": uid, "token": token, "new_password": NEW_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_reset_password_token_is_invalidated_by_use(self):
        uid = encode_uid(self.user.pk)
        token = password_reset_token.make_token(self.user)

        self.client.post(
            reverse("accounts:reset-password"),
            {"uid": uid, "token": token, "new_password": NEW_PASSWORD},
            format="json",
        )
        # Reusing the same token now fails, since the password hash
        # baked into the token's signature has changed.
        second = self.client.post(
            reverse("accounts:reset-password"),
            {"uid": uid, "token": token, "new_password": "AnotherOne!2"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_rejects_weak_new_password(self):
        uid = encode_uid(self.user.pk)
        token = password_reset_token.make_token(self.user)

        response = self.client.post(
            reverse("accounts:reset-password"),
            {"uid": uid, "token": token, "new_password": "alllowercase"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)