from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Package, ServiceCategory

User = get_user_model()
VALID_PASSWORD = "Str0ng!Passw0rd"


class PackageListingTests(APITestCase):
    """Package listing works — public, published-only."""

    def setUp(self):
        self.category = ServiceCategory.objects.create(name="Test Service Category", slug="test-service-category")
        self.published = Package.objects.create(
            service_category=self.category, tier="BASIC", name="Basic Site",
            slug="basic-site", description="A basic site.", starting_price="299.00",
            delivery_days=7, revision_count=2, support_duration_days=30,
            status=Package.Status.PUBLISHED,
        )
        Package.objects.create(
            service_category=self.category, tier="STANDARD", name="Draft Package",
            slug="draft-package", description="Not ready yet.", starting_price="599.00",
            delivery_days=14, revision_count=3, support_duration_days=30,
            status=Package.Status.DRAFT,
        )

    def test_anonymous_can_list_published_packages(self):
        response = self.client.get(reverse("catalog:packages"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["results"]]
        self.assertIn("Basic Site", names)
        self.assertNotIn("Draft Package", names)

    def test_anonymous_can_view_published_package_detail(self):
        response = self.client.get(reverse("catalog:package-detail", args=["basic-site"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "basic-site")

    def test_draft_package_detail_is_not_found_not_forbidden(self):
        response = self.client.get(reverse("catalog:package-detail", args=["draft-package"]))
        # 404, not 403 — existence of an unpublished package shouldn't
        # be revealed to anonymous visitors either way.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_tier(self):
        response = self.client.get(reverse("catalog:packages"), {"tier": "BASIC"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(p["tier"] == "BASIC" for p in response.data["results"]))


class PackageAdminCreateTests(APITestCase):
    """Package creation works — admin-only."""

    def setUp(self):
        self.category = ServiceCategory.objects.create(name="Test Service Category 2", slug="test-service-category-2")
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password=VALID_PASSWORD,
            role="ADMIN", is_staff=True, is_active=True, is_email_verified=True,
        )
        self.customer = User.objects.create_user(
            username="cust", email="cust@example.com", password=VALID_PASSWORD,
            role="CUSTOMER", is_active=True, is_email_verified=True,
        )

    def _payload(self, **overrides):
        payload = {
            "service_category": self.category.id, "tier": "PREMIUM", "name": "Premium Site",
            "slug": "premium-site", "description": "The works.", "starting_price": "1999.00",
            "delivery_days": 21, "revision_count": 5, "support_duration_days": 90,
        }
        payload.update(overrides)
        return payload

    def test_admin_can_create_package(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("catalog:admin-packages"), self._payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        package = Package.all_objects.get(slug="premium-site")
        self.assertEqual(package.status, Package.Status.DRAFT)  # created as draft, not auto-published
        self.assertEqual(package.created_by, self.admin)

    def test_customer_cannot_create_package(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("catalog:admin-packages"), self._payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_publish_and_hide_package(self):
        self.client.force_authenticate(self.admin)
        create = self.client.post(reverse("catalog:admin-packages"), self._payload(), format="json")
        package_id = create.data["id"] if "id" in create.data else Package.all_objects.get(slug="premium-site").id

        publish = self.client.post(reverse("catalog:admin-package-publish", args=[package_id]))
        self.assertEqual(publish.status_code, status.HTTP_200_OK)
        self.assertEqual(Package.all_objects.get(id=package_id).status, Package.Status.PUBLISHED)

        hide = self.client.post(reverse("catalog:admin-package-hide", args=[package_id]))
        self.assertEqual(hide.status_code, status.HTTP_200_OK)
        self.assertEqual(Package.all_objects.get(id=package_id).status, Package.Status.HIDDEN)

    def test_rejects_non_positive_price(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("catalog:admin-packages"), self._payload(starting_price="0.00"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_one_package_per_tier_per_category(self):
        self.client.force_authenticate(self.admin)
        Package.objects.create(
            service_category=self.category, tier="PREMIUM", name="Existing Premium",
            slug="existing-premium", description="x", starting_price="1000.00",
            delivery_days=10, revision_count=2, support_duration_days=30,
        )
        response = self.client.post(
            reverse("catalog:admin-packages"), self._payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)