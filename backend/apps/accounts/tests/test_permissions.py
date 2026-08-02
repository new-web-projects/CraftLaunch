from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

VALID_PASSWORD = "Str0ng!Passw0rd"


class MeEndpointPermissionTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="cust", email="cust@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.developer = User.objects.create_user(
            username="dev", email="dev@example.com", password=VALID_PASSWORD,
            role="DEVELOPER", is_active=True, is_email_verified=True,
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("accounts:me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_sees_customer_profile_shape(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("accounts:me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "CUSTOMER")
        self.assertIn("profile", response.data)

    def test_developer_and_customer_profiles_are_separate_tables(self):
        from apps.accounts.models import CustomerProfile, DeveloperProfile

        self.client.force_authenticate(self.customer)
        self.client.get(reverse("accounts:me"))
        self.client.force_authenticate(self.developer)
        self.client.get(reverse("accounts:me"))

        self.assertTrue(CustomerProfile.objects.filter(user=self.customer).exists())
        self.assertFalse(CustomerProfile.objects.filter(user=self.developer).exists())
        self.assertTrue(DeveloperProfile.objects.filter(user=self.developer).exists())
        self.assertFalse(DeveloperProfile.objects.filter(user=self.customer).exists())

    def test_update_profile_only_touches_own_role_profile(self):
        from apps.accounts.models import CustomerProfile

        self.client.force_authenticate(self.customer)
        response = self.client.patch(
            reverse("accounts:me"), {"phone": "+1-555-0100", "country": "US"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profile = CustomerProfile.objects.get(user=self.customer)
        self.assertEqual(profile.phone, "+1-555-0100")
        self.assertEqual(profile.country, "US")


class RolePermissionClassTests(APITestCase):
    """Exercises permissions.py directly against a throwaway view-like
    check, since Part 2 has no role-specific feature endpoints yet
    beyond profile (those arrive with bookings/payments)."""

    def setUp(self):
        self.customer = User.objects.create_user(
            username="cust2", email="cust2@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )
        self.admin = User.objects.create_user(
            username="admin2", email="admin2@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )

    def test_is_customer_permission(self):
        from apps.accounts.permissions import IsAdminRole, IsCustomer

        class Request:
            def __init__(self, user):
                self.user = user

        self.assertTrue(IsCustomer().has_permission(Request(self.customer), None))
        self.assertFalse(IsCustomer().has_permission(Request(self.admin), None))
        self.assertFalse(IsAdminRole().has_permission(Request(self.customer), None))
        self.assertTrue(IsAdminRole().has_permission(Request(self.admin), None))

    def test_is_super_admin_permission_checks_is_superuser_not_role(self):
        from apps.accounts.permissions import IsSuperAdmin

        class Request:
            def __init__(self, user):
                self.user = user

        # self.admin has role=ADMIN but is not a Django superuser.
        self.assertFalse(IsSuperAdmin().has_permission(Request(self.admin), None))

        super_admin = User.objects.create_superuser(
            username="root2", email="root2@example.com", password=VALID_PASSWORD
        )
        self.assertTrue(IsSuperAdmin().has_permission(Request(super_admin), None))