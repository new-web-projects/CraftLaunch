"""
Proves get_storage_backend() (apps/bookings/storage.py) actually reads
apps.configuration's StorageConfiguration — the concrete, testable
version of Part 4's "Switch Storage Provider" and "no restart
required" requirements. Before this, changing StorageConfiguration
via the admin API saved a value nothing ever read; uploads still used
whatever STORAGE_PROVIDER was set to at process start.
"""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase

from apps.bookings.storage import LocalStorageBackend, get_storage_backend
from apps.configuration.models import StorageConfiguration


class StorageBackendSwitchingTests(TestCase):
    def tearDown(self):
        # Django's TestCase rolls back the DB transaction between
        # tests but doesn't touch the cache — get_storage_backend()
        # reads StorageConfiguration through apps.configuration's
        # cached service layer, so a save() here can leak its cached
        # value into whichever test runs next without this. Same
        # pattern as apps/configuration/tests/test_api.py's tearDown.
        cache.clear()

    def test_default_configuration_returns_local_backend(self):
        backend = get_storage_backend()
        self.assertIsInstance(backend, LocalStorageBackend)

    @patch("boto3.client")
    def test_switching_active_provider_to_s3_takes_effect_immediately(self, mock_boto_client):
        mock_boto_client.return_value = MagicMock()

        config = StorageConfiguration.load()
        config.active_provider = "S3"
        config.s3_access_key_id = "AKIAFAKE"
        config.s3_secret_access_key = "fakesecret"
        config.s3_bucket_name = "my-bucket"
        config.s3_region = "ap-south-1"
        config.save()

        backend = get_storage_backend()

        self.assertEqual(backend.provider_name, "S3")
        mock_boto_client.assert_called_once_with(
            "s3",
            aws_access_key_id="AKIAFAKE",
            aws_secret_access_key="fakesecret",
            region_name="ap-south-1",
        )

    @patch("cloudinary.config")
    def test_switching_active_provider_to_cloudinary_takes_effect_immediately(self, mock_config):
        config = StorageConfiguration.load()
        config.active_provider = "CLOUDINARY"
        config.cloudinary_cloud_name = "demo"
        config.cloudinary_api_key = "123456"
        config.cloudinary_api_secret = "fakesecret"
        config.save()

        backend = get_storage_backend()

        self.assertEqual(backend.provider_name, "CLOUDINARY")
        mock_config.assert_called_once_with(
            cloud_name="demo", api_key="123456", api_secret="fakesecret", secure=True
        )

    def test_switching_back_to_local_takes_effect_immediately(self):
        config = StorageConfiguration.load()
        config.active_provider = "S3"
        config.save()
        config.active_provider = "LOCAL"
        config.save()

        backend = get_storage_backend()
        self.assertIsInstance(backend, LocalStorageBackend)
