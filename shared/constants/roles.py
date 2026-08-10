"""
Canonical role and enum names for CraftLaunch.

The Python half of a value that must mean the same thing on both sides
of the stack — see /shared/README.md for why this is duplicated rather
than imported directly, and keep this file and shared/constants/roles.ts
in sync by hand until a codegen step replaces that convention.

ROLES is live as of Part 2 — apps/accounts/models.py defines its role
field using Django's own TextChoices, matching these exact values:

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DEVELOPER = "DEVELOPER", "Developer"
        CUSTOMER = "CUSTOMER", "Customer"

STORAGE_PROVIDERS is live as of Part 3 — apps/bookings/storage.py
dispatches on config/settings/base.py's STORAGE_PROVIDER setting
(env-configured, defaulting to "LOCAL") using these same three values:

    STORAGE_BACKENDS = {
        "LOCAL": LocalStorageBackend,
        "S3": S3StorageBackend,
        "CLOUDINARY": CloudinaryStorageBackend,
    }

As with ROLES, this happens via an independently-maintained value in
that file rather than an import of this one — see /shared/README.md.
"""

ROLES = ("ADMIN", "DEVELOPER", "CUSTOMER")

STORAGE_PROVIDERS = ("LOCAL", "S3", "CLOUDINARY")