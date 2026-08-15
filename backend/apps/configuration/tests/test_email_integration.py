from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase

from apps.accounts.emails import send_verification_email
from apps.configuration.models import SiteConfiguration

User = get_user_model()


class DynamicSiteNameInEmailTests(TestCase):
    """Proves apps/accounts/emails.py actually reads the admin-configured
    website name (not just that it doesn't crash) — the concrete,
    testable version of Part 4's "no hardcoded branding" requirement."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="emailtest", email="emailtest@example.com", password="Str0ng!Passw0rd",
            role="CUSTOMER", is_active=True,
        )

    def tearDown(self):
        # Django's TestCase rolls back the DB transaction between
        # tests but doesn't touch the cache — without this, a save()
        # here can leak its cached SiteConfiguration into whichever
        # test happens to run next. See ConfigurationCacheTests in
        # test_models.py for the same pattern.
        cache.clear()

    def test_email_uses_default_site_name_when_unconfigured(self):
        send_verification_email(self.user)
        self.assertIn("CraftLaunch", mail.outbox[0].subject)

    def test_email_uses_admin_configured_site_name(self):
        config = SiteConfiguration.load()
        config.website_name = "Acme Web Studio"
        config.save()

        send_verification_email(self.user)

        self.assertIn("Acme Web Studio", mail.outbox[0].subject)
        self.assertNotIn("CraftLaunch", mail.outbox[0].subject)
