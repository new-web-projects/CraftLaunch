"""
Storage provider abstraction. get_storage_backend() reads the active
provider and its credentials from apps.configuration's StorageConfiguration
(database-backed, admin-editable, cached — see apps/configuration/services.py)
rather than the STORAGE_PROVIDER env var directly, so switching
providers or rotating credentials takes effect on the next request,
no restart required — this is what Part 4's "Switch Storage Provider"
requirement actually needs, not just a place to save the preference.
STORAGE_PROVIDER (config/settings/base.py) and the AWS_*/CLOUDINARY_*
env vars remain as the seed values apps/configuration's 0002_seed_from_env
migration reads once, and as the fallback if that app's tables aren't
reachable for any reason (see the except clause below) — same interim-
then-database pattern as SITE_NAME, see docs/ARCHITECTURE.md.

Callers (services.py, apps/configuration/views.py) only ever talk to
`get_storage_backend()` and the `StorageBackend` protocol — none of
them import boto3 or cloudinary directly, so switching providers never
touches calling code.

Each ProjectAttachment records which provider it was actually saved
under (models.py `storage_provider`), so files uploaded before a
provider switch keep resolving correctly afterwards.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import BinaryIO, Protocol

from django.conf import settings


@dataclass(frozen=True)
class StoredFile:
    provider: str
    key: str
    url: str


class StorageBackend(Protocol):
    provider_name: str

    def save(self, key: str, file: BinaryIO, content_type: str) -> StoredFile: ...
    def url(self, key: str) -> str: ...
    def delete(self, key: str) -> None: ...


def build_storage_key(booking_id, filename: str) -> str:
    """`bookings/<booking_id>/<uuid>-<filename>` — collision-proof
    across concurrent uploads without a DB round trip to generate."""
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"bookings/{booking_id}/{uuid.uuid4()}-{safe_name}"


class LocalStorageBackend:
    """Default backend — no cloud credentials required. Wraps Django's
    own default_storage (FileSystemStorage under MEDIA_ROOT)."""

    provider_name = "LOCAL"

    def save(self, key: str, file: BinaryIO, content_type: str) -> StoredFile:
        from django.core.files.storage import default_storage

        saved_path = default_storage.save(key, file)
        return StoredFile(provider=self.provider_name, key=saved_path, url=self.url(saved_path))

    def url(self, key: str) -> str:
        from django.core.files.storage import default_storage

        return default_storage.url(key)

    def delete(self, key: str) -> None:
        from django.core.files.storage import default_storage

        default_storage.delete(key)


class S3StorageBackend:
    provider_name = "S3"

    def __init__(self, bucket: str, access_key_id: str, secret_access_key: str, region: str):
        import boto3

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region or None,
        )

    def save(self, key: str, file: BinaryIO, content_type: str) -> StoredFile:
        self._client.upload_fileobj(file, self._bucket, key, ExtraArgs={"ContentType": content_type})
        return StoredFile(provider=self.provider_name, key=key, url=self.url(key))

    def url(self, key: str) -> str:
        # Presigned, time-limited — attachments are private, not
        # served from a public bucket/CDN.
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=3600
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


class CloudinaryStorageBackend:
    provider_name = "CLOUDINARY"

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        import cloudinary

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    def save(self, key: str, file: BinaryIO, content_type: str) -> StoredFile:
        import cloudinary.uploader

        # resource_type="auto" handles the full attachment surface
        # (images, PDF, ZIP, DOCX, spreadsheets, text) — Cloudinary
        # only auto-detects raw vs. image/video with this setting.
        result = cloudinary.uploader.upload(file, public_id=key, resource_type="auto", overwrite=False)
        return StoredFile(provider=self.provider_name, key=key, url=result["secure_url"])

    def url(self, key: str) -> str:
        import cloudinary.utils

        url, _ = cloudinary.utils.cloudinary_url(key, resource_type="auto", secure=True)
        return url

    def delete(self, key: str) -> None:
        import cloudinary.uploader

        cloudinary.uploader.destroy(key, resource_type="auto")


def get_storage_backend() -> StorageBackend:
    try:
        # Lazy import, matching this file's existing style for
        # boto3/cloudinary — avoids a module-level dependency between
        # apps.bookings and apps.configuration purely for import
        # ordering, even though there's no actual circular import here.
        from apps.configuration.services import get_storage_configuration

        config = get_storage_configuration()
        provider = config.active_provider
        if provider == "S3":
            return S3StorageBackend(
                bucket=config.s3_bucket_name,
                access_key_id=config.s3_access_key_id,
                secret_access_key=config.s3_secret_access_key,
                region=config.s3_region,
            )
        if provider == "CLOUDINARY":
            return CloudinaryStorageBackend(
                cloud_name=config.cloudinary_cloud_name,
                api_key=config.cloudinary_api_key,
                api_secret=config.cloudinary_api_secret,
            )
        return LocalStorageBackend()
    except Exception:
        # apps.configuration's table not reachable for any reason
        # (mid-migration, or that app somehow not installed) — fall
        # back to the original env-based selection rather than break
        # every attachment upload over an unrelated app's hiccup.
        provider = getattr(settings, "STORAGE_PROVIDER", "LOCAL")
        if provider == "S3":
            return S3StorageBackend(
                bucket=settings.AWS_STORAGE_BUCKET_NAME,
                access_key_id=settings.AWS_ACCESS_KEY_ID,
                secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region=settings.AWS_S3_REGION_NAME,
            )
        if provider == "CLOUDINARY":
            return CloudinaryStorageBackend(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
            )
        return LocalStorageBackend()