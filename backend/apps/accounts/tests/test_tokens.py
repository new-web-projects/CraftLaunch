from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.accounts.models import UserSession

User = get_user_model()

VALID_PASSWORD = "Str0ng!Passw0rd"


class TokenTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="janedoe",
            email="jane@example.com",
            password=VALID_PASSWORD,
            role="CUSTOMER",
            is_active=True,
            is_email_verified=True,
        )
        login = self.client.post(
            reverse("accounts:login"),
            {"identifier": "janedoe", "password": VALID_PASSWORD},
            format="json",
        )
        self.access_token = login.data["access"]

    def _auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def test_refresh_issues_new_access_token_and_rotates_cookie(self):
        old_cookie = self.client.cookies["craftlaunch_refresh"].value
        response = self.client.post(reverse("accounts:refresh"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        new_cookie = response.cookies["craftlaunch_refresh"].value
        self.assertNotEqual(old_cookie, new_cookie)

    def test_refresh_without_cookie_fails(self):
        self.client.cookies.clear()
        response = self.client.post(reverse("accounts:refresh"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_and_clears_session(self):
        self._auth()
        response = self.client.post(reverse("accounts:logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 0)

        # The now-blacklisted refresh token can no longer be refreshed.
        refresh_response = self.client.post(reverse("accounts:refresh"))
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_all_blacklists_every_outstanding_token(self):
        # Log in from a "second device" too.
        self.client.post(
            reverse("accounts:login"),
            {"identifier": "janedoe", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 2)

        self._auth()
        response = self.client.post(reverse("accounts:logout-all"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 0)
        outstanding = OutstandingToken.objects.filter(user=self.user)
        blacklisted = BlacklistedToken.objects.filter(token__user=self.user)
        self.assertEqual(outstanding.count(), blacklisted.count())

    def test_logout_requires_authentication(self):
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)