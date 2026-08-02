"""
Storage provider abstraction. STORAGE_PROVIDER (env-configured today;
Admin-Panel-configurable once the Settings model exists — same interim
pattern as SITE_NAME, see docs/ARCHITECTURE.md) selects between LOCAL,
S3 and CLOUDINARY at runtime. Callers (services.py, views.py) only
ever talk to `get_storage_backend()` and the `StorageBackend`
protocol — none of them import boto3 or cloudinary directly, so
switching providers never touches calling code.

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

    def __init__(self):
        import boto3

        self._bucket = settings.AWS_STORAGE_BUCKET_NAME
        self._client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
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

    def __init__(self):
        import cloudinary

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
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


_BACKENDS: dict[str, type] = {
    "LOCAL": LocalStorageBackend,
    "S3": S3StorageBackend,
    "CLOUDINARY": CloudinaryStorageBackend,
}


def get_storage_backend() -> StorageBackend:
    provider = getattr(settings, "STORAGE_PROVIDER", "LOCAL")
    backend_cls = _BACKENDS.get(provider, LocalStorageBackend)
    return backend_cls()