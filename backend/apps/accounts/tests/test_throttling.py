from unittest import mock

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.throttling import LoginRateThrottle


class LoginThrottleTests(APITestCase):
    """
    Isolated on purpose: the rest of the suite disables throttling
    entirely (see settings/test.py DEFAULT_THROTTLE_RATES=None) because
    LocMemCache persists for the whole test run and would otherwise
    make unrelated tests flaky. This test patches LoginRateThrottle's
    rate directly rather than via override_settings — DRF snapshots
    THROTTLE_RATES onto the throttle class at import time, so changing
    the REST_FRAMEWORK setting afterwards doesn't retroactively update
    an already-imported throttle class.
    """

    def setUp(self):
        cache.clear()
        patcher = mock.patch.dict(LoginRateThrottle.THROTTLE_RATES, {"login": "3/min"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(cache.clear)

    def test_login_is_throttled_after_rate_exceeded(self):
        url = reverse("accounts:login")
        payload = {"identifier": "nobody", "password": "wrong"}

        responses = [self.client.post(url, payload, format="json") for _ in range(3)]
        for response in responses:
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        throttled = self.client.post(url, payload, format="json")
        self.assertEqual(throttled.status_code, status.HTTP_429_TOO_MANY_REQUESTS)