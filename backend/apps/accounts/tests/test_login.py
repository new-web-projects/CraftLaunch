from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import UserSession

User = get_user_model()

VALID_PASSWORD = "Str0ng!Passw0rd"


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="janedoe",
            email="jane@example.com",
            password=VALID_PASSWORD,
            role="CUSTOMER",
            is_active=True,
            is_email_verified=True,
        )

    def test_login_with_email_succeeds(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"identifier": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("craftlaunch_refresh", response.cookies)
        self.assertTrue(response.cookies["craftlaunch_refresh"]["httponly"])

    def test_login_with_username_succeeds(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"identifier": "janedoe", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_creates_a_session_record(self):
        self.client.post(
            reverse("accounts:login"),
            {"identifier": "janedoe", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)

    def test_remember_me_extends_refresh_cookie_lifetime(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"identifier": "janedoe", "password": VALID_PASSWORD, "remember_me": True},
            format="json",
        )
        cookie = response.cookies["craftlaunch_refresh"]
        # A session cookie (remember_me=False) has no max-age at all;
        # remembering one should set a long-lived one.
        self.assertNotEqual(cookie["max-age"], "")

    def test_wrong_password_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"identifier": "janedoe", "password": "WrongPassword!1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["code"], "invalid_credentials")

    def test_unverified_account_cannot_login(self):
        User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password=VALID_PASSWORD,
            role="CUSTOMER",
            is_active=False,
            is_email_verified=False,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"identifier": "unverified", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "email_not_verified")

    def test_account_locks_after_repeated_failures(self):
        url = reverse("accounts:login")
        for _ in range(5):
            self.client.post(url, {"identifier": "janedoe", "password": "wrong"}, format="json")

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked())

        response = self.client.post(
            url, {"identifier": "janedoe", "password": VALID_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)

    def test_successful_login_resets_failed_attempts(self):
        url = reverse("accounts:login")
        self.client.post(url, {"identifier": "janedoe", "password": "wrong"}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)

        self.client.post(url, {"identifier": "janedoe", "password": VALID_PASSWORD}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)