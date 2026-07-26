from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "craftlaunch-api", "version": "0.1.0"},
        )

    def test_health_check_requires_no_authentication(self):
        # Anonymous, unauthenticated client (the default test client) must
        # be able to reach this — it's the whole point of a liveness probe.
        response = self.client.get(reverse("health-check"))
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)
