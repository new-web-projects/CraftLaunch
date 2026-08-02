"""
Bookings: the order/transaction side of the marketplace. References
apps.catalog (Package, WebsiteCategory, WebsiteType, WebsiteFeature) by
FK but never the reverse — catalog has no idea bookings exist, which
is the dependency direction Clean Architecture asks for here (the
sellable-things layer doesn't depend on the orders layer).

No payment models in this part by design (a later part) — Booking
tracks status/workflow only, nothing about money changing hands beyond
the price already visible on the Package it references.
"""

from django.conf import settings
from django.db import models

from apps.catalog.models import Package, WebsiteCategory, WebsiteFeature, WebsiteType
from apps.core.models import SoftDeleteManager, SoftDeleteModel, SoftDeleteQuerySet, TimeStampedModel, UUIDModel


class ProjectStatus(models.Model):
    """
    Admin-configurable status catalog rather than a hardcoded
    TextChoices enum — matches the "everything admin-editable" goal
    from Part 1's spec. Booking.status is a FK here, not a CharField,
    so adding/reordering a workflow status later is a data change, not
    a code change. Seeded with the exact 9 statuses the spec lists via
    a data migration (0002_seed_project_status.py) — this table isn't
    meant to be created empty.
    """

    code = models.SlugField(max_length=30, unique=True)
    label = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_terminal = models.BooleanField(
        default=False, help_text="No further transitions expected once a booking reaches this status."
    )
    is_default = models.BooleanField(
        default=False, help_text="Status assigned to a brand-new booking."
    )
    color = models.CharField(max_length=20, blank=True, default="", help_text="Badge color hint for the UI.")

    class Meta:
        ordering = ["sort_order"]
        verbose_name_plural = "project statuses"
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"], condition=models.Q(is_default=True), name="unique_default_status"
            ),
        ]

    def __str__(self):
        return self.label

    @classmethod
    def get_default(cls) -> "ProjectStatus":
        return cls.objects.get(is_default=True)


class BookingQuerySet(SoftDeleteQuerySet):
    def for_customer(self, user):
        return self.alive().filter(customer=user)

    def for_developer(self, user):
        return self.alive().filter(developer_assignments__developer=user, developer_assignments__is_active=True)

    def for_user(self, user):
        """Role-scoped visibility in one call: admin sees everything,
        a developer sees bookings they're assigned to, a customer sees
        their own. Used everywhere a Booking is looked up by pk so an
        unrelated user's request 404s (the row isn't in their scoped
        queryset at all) rather than 403ing after the fact — a
        private booking's existence isn't confirmed to someone who
        has no business knowing about it, same principle as
        catalog.Package.objects.published() for unpublished packages."""
        if user.role == "ADMIN":
            return self.alive()
        if user.role == "DEVELOPER":
            return self.for_developer(user)
        return self.for_customer(user)


class BookingManager(SoftDeleteManager):
    def get_queryset(self):
        return BookingQuerySet(self.model, using=self._db).alive()

    def for_customer(self, user):
        return self.get_queryset().for_customer(user)

    def for_developer(self, user):
        return self.get_queryset().for_developer(user)

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class Booking(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """
    The core order record. UUID PK: this is private, customer-owned
    data referenced directly in URLs (/bookings/<uuid>), unlike the
    public catalog it points into.
    """

    class BusinessType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        STARTUP = "STARTUP", "Startup"
        SMALL_BUSINESS = "SMALL_BUSINESS", "Small business"
        ENTERPRISE = "ENTERPRISE", "Enterprise"
        NON_PROFIT = "NON_PROFIT", "Non-profit"
        OTHER = "OTHER", "Other"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
        limit_choices_to={"role": "CUSTOMER"},
    )
    package = models.ForeignKey(Package, on_delete=models.PROTECT, related_name="bookings")
    website_category = models.ForeignKey(WebsiteCategory, on_delete=models.PROTECT, related_name="bookings")
    website_type = models.ForeignKey(
        WebsiteType, on_delete=models.PROTECT, related_name="bookings", null=True, blank=True
    )
    status = models.ForeignKey(ProjectStatus, on_delete=models.PROTECT, related_name="bookings")

    website_name = models.CharField(max_length=150)
    business_name = models.CharField(max_length=150)
    business_type = models.CharField(max_length=20, choices=BusinessType.choices)
    description = models.TextField()
    preferred_delivery_date = models.DateField(null=True, blank=True)

    # List of {"label": str, "url": str} — validated in
    # bookings/validators.py, not at the model level, so DRF returns a
    # clean per-item error instead of a generic JSON schema failure.
    reference_links = models.JSONField(default=list, blank=True)

    # Client-generated (frontend/src/lib/idempotency.ts), sent as a
    # header on create — lets BookingService reject an accidental
    # double-submit (double-click, retried request) without the
    # customer ending up with two identical bookings.
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)

    required_features = models.ManyToManyField(
        WebsiteFeature, through="BookingRequirement", related_name="bookings"
    )

    objects = BookingManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.website_name} ({self.customer.username})"


class BookingRequirement(models.Model):
    """Through table: which WebsiteFeatures a customer selected as
    required for their booking (structured — compare with
    CustomerRequirement below for the free-form equivalent)."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="booking_requirements")
    website_feature = models.ForeignKey(
        WebsiteFeature, on_delete=models.PROTECT, related_name="booking_requirements"
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "website_feature"], name="unique_feature_per_booking"
            ),
        ]

    def __str__(self):
        return f"{self.booking_id} — {self.website_feature.name}"


class CustomerRequirement(models.Model):
    """
    Free-form custom requirement attached to a booking — for asks that
    don't map to the standard WebsiteFeature catalog (e.g. "integrate
    with our existing CRM"). Plain integer PK: always accessed via its
    parent booking, never referenced directly by URL.
    """

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="customer_requirements")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-priority", "created_at"]

    def __str__(self):
        return self.title


class ProjectAttachment(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """
    A file uploaded against a booking. UUID PK: referenced directly in
    upload/download/delete URLs. Storage is abstracted (see
    bookings/storage.py) — `storage_provider` is recorded per-file at
    upload time so files uploaded under one provider still resolve
    correctly even after an admin switches the active provider later;
    nothing here assumes S3 or Cloudinary specifically.
    """

    class FileCategory(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        PDF = "PDF", "PDF"
        ZIP = "ZIP", "ZIP archive"
        DOCX = "DOCX", "Word document"
        SPREADSHEET = "SPREADSHEET", "Spreadsheet"
        TEXT = "TEXT", "Text file"

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="uploaded_attachments"
    )

    storage_provider = models.CharField(max_length=20)
    storage_key = models.CharField(max_length=500)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_category = models.CharField(max_length=20, choices=FileCategory.choices)
    file_size = models.PositiveBigIntegerField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["booking", "-created_at"])]

    def __str__(self):
        return self.original_filename


class BookingTimeline(models.Model):
    """
    Append-only event log per booking — the audit trail the spec asks
    to have "considered". No `updated_at`: timeline entries are
    immutable by design, so a TimeStampedModel's auto_now field would
    be meaningless here.
    """

    class EventType(models.TextChoices):
        BOOKING_CREATED = "BOOKING_CREATED", "Booking created"
        STATUS_CHANGED = "STATUS_CHANGED", "Status changed"
        NOTE_ADDED = "NOTE_ADDED", "Note added"
        FILE_UPLOADED = "FILE_UPLOADED", "File uploaded"
        FILE_DELETED = "FILE_DELETED", "File deleted"
        DEVELOPER_ASSIGNED = "DEVELOPER_ASSIGNED", "Developer assigned"
        DEVELOPER_UNASSIGNED = "DEVELOPER_UNASSIGNED", "Developer unassigned"
        BOOKING_CANCELLED = "BOOKING_CANCELLED", "Booking cancelled"

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="timeline_events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="booking_timeline_events"
    )
    from_status = models.ForeignKey(
        ProjectStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    to_status = models.ForeignKey(
        ProjectStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["booking", "-created_at"])]

    def __str__(self):
        return f"{self.booking_id} — {self.get_event_type_display()}"


class BookingNote(models.Model):
    """A comment on a booking — either visible to the customer, or
    `is_internal=True` for admin/developer-only discussion."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    content = models.TextField()
    is_internal = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Note on {self.booking_id} by {self.author}"


class DeveloperAssignment(models.Model):
    """Which developer(s) are assigned to a booking, and by whom.
    `is_active=False` marks a past/ended assignment rather than
    deleting the row, preserving history."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="developer_assignments")
    developer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="developer_assignments",
        limit_choices_to={"role": "DEVELOPER"},
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    role_note = models.CharField(max_length=100, blank=True, default="")
    assigned_at = models.DateTimeField(auto_now_add=True)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "developer"],
                condition=models.Q(is_active=True),
                name="unique_active_assignment_per_developer",
            ),
        ]

    def __str__(self):
        return f"{self.developer} on {self.booking_id}"