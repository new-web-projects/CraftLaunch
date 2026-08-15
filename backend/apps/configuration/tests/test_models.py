from django.core.cache import cache
from django.test import TestCase

from apps.configuration import services
from apps.configuration.models import FeatureFlags, SiteConfiguration, StorageConfiguration


class SingletonModelTests(TestCase):
    def test_load_returns_pk_1(self):
        # The 0002_seed_from_env data migration means a freshly
        # migrated database already has row 1 for every configuration
        # model (seeded from the env-configured settings it replaces
        # — see that migration) rather than genuinely empty tables, so
        # this checks load()'s contract (always returns pk=1) instead
        # of asserting a pre-seed-migration "table starts empty" state
        # that's no longer accurate.
        instance = SiteConfiguration.load()
        self.assertEqual(instance.pk, 1)
        self.assertEqual(SiteConfiguration.objects.count(), 1)

    def test_load_returns_same_row_on_subsequent_calls(self):
        first = SiteConfiguration.load()
        first.website_name = "Changed"
        first.save()

        second = SiteConfiguration.load()
        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.website_name, "Changed")
        self.assertEqual(SiteConfiguration.objects.count(), 1)

    def test_save_always_forces_pk_1(self):
        # Mutating a real loaded instance's pk (rather than
        # constructing a bare SiteConfiguration(pk=99, ...)) so
        # created_at — a real column, unrelated to what this test is
        # actually checking — is already populated from the DB
        # instead of tripping its own NOT NULL constraint.
        instance = SiteConfiguration.load()
        instance.pk = 99
        instance.website_name = "Attempted second row"
        instance.save()
        self.assertEqual(instance.pk, 1)
        self.assertEqual(SiteConfiguration.objects.count(), 1)

    def test_delete_is_a_no_op(self):
        instance = SiteConfiguration.load()
        instance.delete()
        self.assertEqual(SiteConfiguration.objects.count(), 1)

    def test_fresh_database_returns_field_defaults(self):
        # No fixture, no prior save — this is the "Website Name
        # updates instantly" requirement's other half: a totally
        # fresh install must have *something* sane to render before
        # any admin ever visits a settings page.
        flags = FeatureFlags.load()
        self.assertTrue(flags.booking_enabled)
        self.assertFalse(flags.maintenance_mode)


class EncryptedFieldTests(TestCase):
    def test_secret_round_trips_through_the_database(self):
        config = StorageConfiguration.load()
        config.s3_secret_access_key = "super-secret-value-123"
        config.save()

        reloaded = StorageConfiguration.objects.get(pk=1)
        self.assertEqual(reloaded.s3_secret_access_key, "super-secret-value-123")

    def test_value_is_actually_encrypted_in_the_database(self):
        config = StorageConfiguration.load()
        config.s3_secret_access_key = "super-secret-value-123"
        config.save()

        # Read the raw column value, bypassing the model's
        # from_db_value decryption, to prove the plaintext isn't
        # sitting in the table as-is.
        with self.settings():
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT s3_secret_access_key FROM configuration_storageconfiguration WHERE id = 1"
                )
                raw_value = cursor.fetchone()[0]

        self.assertNotEqual(raw_value, "super-secret-value-123")
        self.assertNotIn("super-secret-value-123", raw_value)

    def test_blank_secret_is_not_encrypted(self):
        config = StorageConfiguration.load()
        config.s3_secret_access_key = ""
        config.save()
        reloaded = StorageConfiguration.objects.get(pk=1)
        self.assertEqual(reloaded.s3_secret_access_key, "")

    def test_wrong_key_decrypts_to_empty_rather_than_raising(self):
        config = StorageConfiguration.load()
        config.s3_secret_access_key = "super-secret-value-123"
        config.save()

        # Simulate CONFIGURATION_ENCRYPTION_KEY having changed since
        # this row was written by encrypting with a different key
        # directly, bypassing the model.
        from cryptography.fernet import Fernet

        from django.db import connection

        other_key_ciphertext = Fernet(Fernet.generate_key()).encrypt(b"unreadable-now").decode()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE configuration_storageconfiguration SET s3_secret_access_key = %s WHERE id = 1",
                [other_key_ciphertext],
            )

        reloaded = StorageConfiguration.objects.get(pk=1)
        self.assertEqual(reloaded.s3_secret_access_key, "")


class ConfigurationCacheTests(TestCase):
    def tearDown(self):
        cache.clear()

    def test_get_site_configuration_is_cached(self):
        services.get_site_configuration()
        cache_key = services.CACHE_KEYS[SiteConfiguration]
        self.assertIsNotNone(cache.get(cache_key))

    def test_saving_invalidates_the_cache(self):
        site = services.get_site_configuration()
        cache_key = services.CACHE_KEYS[SiteConfiguration]
        self.assertIsNotNone(cache.get(cache_key))

        site.website_name = "New Name"
        site.save()

        # The post_save signal (signals.py) should have cleared this.
        self.assertIsNone(cache.get(cache_key))

    def test_next_read_after_save_reflects_the_change(self):
        site = services.get_site_configuration()
        site.website_name = "New Name"
        site.save()

        refreshed = services.get_site_configuration()
        self.assertEqual(refreshed.website_name, "New Name")
