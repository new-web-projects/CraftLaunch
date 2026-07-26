"""
Canonical role and enum names for CraftLaunch.

The Python half of a value that must mean the same thing on both sides
of the stack — see /shared/README.md for why this is duplicated rather
than imported directly, and keep this file and shared/constants/roles.ts
in sync by hand until a codegen step replaces that convention.

Not consumed by any code yet: no User model exists until a later part.
When it does, apps/accounts/models.py should define its role field
using Django's own TextChoices, matching these exact values:

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DEVELOPER = "DEVELOPER", "Developer"
        CUSTOMER = "CUSTOMER", "Customer"
"""

ROLES = ("ADMIN", "DEVELOPER", "CUSTOMER")

STORAGE_PROVIDERS = ("S3", "CLOUDINARY")
