"""
At-rest encryption for the secret fields on the configuration models
(SMTP password, S3/Cloudinary API secrets, Razorpay key secret and
webhook secret). Everywhere else in this codebase, "secret" means
"never stored at all" (passwords are hashed, not encrypted — see
apps/accounts/managers.py). These are different: unlike a login
password, the application needs the *original* SMTP password back to
actually authenticate with a mail server, so hashing isn't an option.
Symmetric encryption is the standard answer for "the app needs the
plaintext back, but a database dump or read-replica leak shouldn't
hand it over for free."

Serializers are the other half of this: EncryptedTextField only
protects the value at rest in Postgres. CharSecretField in
serializers.py makes sure these values are also write_only, so they
never round-trip back out through the API either — see that file's
docstring.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _derive_fernet_key() -> bytes:
    """
    Fernet requires a 32-byte urlsafe-base64 key. CONFIGURATION_ENCRYPTION_KEY
    is meant to be exactly that, generated once via
    `Fernet.generate_key()` and set as an env var — see .env.example.

    If it's not set, dev/test still needs to work with zero setup
    (same philosophy as every other setting in config/settings/base.py),
    so this derives a key from SECRET_KEY instead: SHA-256 always
    produces exactly 32 bytes, which is exactly what Fernet's raw key
    material needs before base64-encoding. This is *not* the intended
    production path — SECRET_KEY rotating would silently make every
    encrypted field unreadable — production.py's env loading is
    expected to always set CONFIGURATION_ENCRYPTION_KEY explicitly.
    """
    raw = getattr(settings, "CONFIGURATION_ENCRYPTION_KEY", None)
    if raw:
        return raw.encode() if isinstance(raw, str) else raw
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_derive_fernet_key())


class EncryptedTextField(models.TextField):
    """
    Encrypts on write, decrypts on read — transparent to everything
    above the ORM. Model code reads `instance.smtp_password` and gets
    the real plaintext value back; only the column in Postgres holds
    ciphertext. Blank values are stored as an empty string rather than
    encrypted, so "never configured" stays distinguishable from
    "configured with an empty secret" without every caller needing to
    know about the encryption layer.
    """

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # CONFIGURATION_ENCRYPTION_KEY changed since this row was
            # written (e.g. SECRET_KEY rotated in an environment that
            # never set an explicit encryption key). Surfacing this as
            # "not configured" is safer than raising mid-request on
            # every settings read across the whole site.
            return ""
