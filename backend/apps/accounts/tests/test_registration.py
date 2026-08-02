from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

VALID_PASSWORD = "Str0ng!Passw0rd"


class RegistrationTests(APITestCase):
    def _payload(self, **overrides):
        payload = {
            "username": "janedoe",
            "email": "jane@example.com",
            "password": VALID_PASSWORD,
            "password_confirm": VALID_PASSWORD,
            "role": "CUSTOMER",
        }
        payload.update(overrides)
        return payload

    def test_customer_registration_creates_inactive_unverified_user_and_sends_email(self):
        response = self.client.post(reverse("accounts:register"), self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="janedoe")
        self.assertEqual(user.role, "CUSTOMER")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertTrue(hasattr(user, "customer_profile"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verify", mail.outbox[0].subject.lower())

    def test_developer_registration_creates_developer_profile(self):
        response = self.client.post(
            reverse("accounts:register"),
            self._payload(username="devdan", email="dev@example.com", role="DEVELOPER"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="devdan")
        self.assertEqual(user.role, "DEVELOPER")
        self.assertTrue(hasattr(user, "developer_profile"))

    def test_public_registration_rejects_admin_role(self):
        response = self.client.post(
            reverse("accounts:register"),
            self._payload(username="wannabe-admin", email="wannabe@example.com", role="ADMIN"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="wannabe-admin").exists())

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("accounts:register"),
            self._payload(password_confirm="SomethingElse!1"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            reverse("accounts:register"),
            self._payload(password="alllowercase", password_confirm="alllowercase"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_duplicate_email(self):
        self.client.post(reverse("accounts:register"), self._payload(), format="json")
        response = self.client.post(
            reverse("accounts:register"),
            self._payload(username="someoneelse"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminRegistrationTests(APITestCase):
    def setUp(self):
        self.super_admin = User.objects.create_superuser(
            username="root", email="root@example.com", password=VALID_PASSWORD
        )
        self.regular_admin = User.objects.create_user(
            username="regularadmin",
            email="regularadmin@example.com",
            password=VALID_PASSWORD,
            role="ADMIN",
            is_staff=True,
            is_active=True,
        )

    def test_super_admin_can_create_admin(self):
        self.client.force_authenticate(self.super_admin)
        response = self.client.post(
            reverse("accounts:register-admin"),
            {
                "username": "newadmin",
                "email": "newadmin@example.com",
                "password": VALID_PASSWORD,
                "password_confirm": VALID_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = User.objects.get(username="newadmin")
        self.assertEqual(created.role, "ADMIN")
        self.assertTrue(created.is_staff)
        self.assertFalse(created.is_superuser)

    def test_regular_admin_cannot_create_admin(self):
        self.client.force_authenticate(self.regular_admin)
        response = self.client.post(
            reverse("accounts:register-admin"),
            {
                "username": "newadmin2",
                "email": "newadmin2@example.com",
                "password": VALID_PASSWORD,
                "password_confirm": VALID_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_admin(self):
        response = self.client.post(
            reverse("accounts:register-admin"),
            {
                "username": "newadmin3",
                "email": "newadmin3@example.com",
                "password": VALID_PASSWORD,
                "password_confirm": VALID_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)