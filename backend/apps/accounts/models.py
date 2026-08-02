from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import UserManager


class Role(models.TextChoices):
    """Must stay identical to shared/constants/roles.{ts,py} — see
    shared/README.md for the cross-language sync convention."""

    ADMIN = "ADMIN", "Admin"
    DEVELOPER = "DEVELOPER", "Developer"
    CUSTOMER = "CUSTOMER", "Customer"


class User(AbstractUser):
    """
    Extends Django's AbstractUser rather than replacing it outright —
    keeps `username`, `is_staff`, `is_superuser`, `is_active`,
    `first_name`/`last_name` and the battle-tested permission
    machinery, and adds only what the spec needs on top:

    - `email` made required + unique (AbstractUser's is neither)
    - `role`: ADMIN / DEVELOPER / CUSTOMER, completely separate from
      Django's own is_staff/is_superuser, which control Django admin
      access specifically (see AdminRegisterSerializer for how the two
      interact for the Admin role)
    - email verification + account-lockout bookkeeping

    USERNAME_FIELD stays "username" (not "email") so Django admin's
    login form and `createsuperuser` keep working unmodified; the
    accounts API itself accepts either email or username at login via
    EmailOrUsernameBackend (see backends.py).
    """

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)

    is_email_verified = models.BooleanField(default=False)

    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    deletion_requested_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.username

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_minutes)
            self.failed_login_attempts = 0
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def register_successful_login(self) -> None:
        if self.failed_login_attempts or self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_attempts", "locked_until"])


class BaseProfile(models.Model):
    """
    Fields every role's profile shares today. Abstract on purpose: each
    role still gets its own physical table (CustomerProfile,
    DeveloperProfile, AdminProfile) rather than one shared table with a
    role column, so role data stays isolated at the database level —
    matching "all roles must have completely isolated permissions" —
    and so each table can grow its own role-specific fields later
    (developer skills/portfolio, customer billing info, ...) without
    touching the others.
    """

    profile_picture_url = models.URLField(blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")  # ISO 3166-1 alpha-2
    timezone = models.CharField(max_length=64, blank=True, default="UTC")
    language = models.CharField(max_length=8, blank=True, default="en")

    class Meta:
        abstract = True


class CustomerProfile(BaseProfile):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile"
    )

    def __str__(self):
        return f"CustomerProfile<{self.user.username}>"


class DeveloperProfile(BaseProfile):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="developer_profile"
    )

    def __str__(self):
        return f"DeveloperProfile<{self.user.username}>"


class AdminProfile(BaseProfile):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_profile"
    )

    def __str__(self):
        return f"AdminProfile<{self.user.username}>"


class UserSession(models.Model):
    """
    One row per issued refresh token, purely so a signed-in user can see
    and individually revoke their own active sessions/devices (the
    spec's "Session Management"). `jti` matches the JTI claim of the
    corresponding SimpleJWT OutstandingToken — revoking a row here also
    blacklists that token; see accounts/views.py SessionRevokeView.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions"
    )
    jti = models.CharField(max_length=255, unique=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]

    def __str__(self):
        return f"Session<{self.user.username}:{self.jti[:8]}>"