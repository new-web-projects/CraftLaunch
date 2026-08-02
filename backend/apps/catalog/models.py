"""
Catalog: the sellable side of the marketplace. apps/bookings holds the
order/transaction side and references these models by FK.

Two "category" concepts are deliberately kept separate rather than
merged into one, because they answer different questions:

  - ServiceCategory: what kind of *work* is being purchased
    (New Website, Redesign, Bug Fix, Maintenance). Packages belong to
    exactly one of these — pricing tiers differ by the kind of work.
  - WebsiteCategory: what *industry/purpose* the resulting website is
    for (E-commerce, Portfolio, Corporate, Blog, ...). A Booking picks
    one of these; it's independent of which service was purchased.

WebsiteType is a third, separate axis: the *structural* kind of build
(Landing Page, Multi-page, Web Application, E-commerce Store) —
independent of both the service purchased and the industry.
"""

from django.db import models

from apps.core.models import SoftDeleteManager, SoftDeleteModel, SoftDeleteQuerySet, TimeStampedModel


class ActiveLookupQuerySet(SoftDeleteQuerySet):
    def active(self):
        return self.alive().filter(is_active=True)


class ActiveLookupManager(SoftDeleteManager):
    def get_queryset(self):
        return ActiveLookupQuerySet(self.model, using=self._db).alive()

    def active(self):
        return self.get_queryset().active()


class LookupModel(TimeStampedModel, SoftDeleteModel):
    """
    Shared shape for the simple admin-managed reference tables
    (ServiceCategory, WebsiteCategory, WebsiteType, Technology, Tag,
    WebsiteFeature). Plain integer PKs on purpose — see the UUIDModel
    docstring in apps/core/models.py for why these differ from Booking
    and its attachments.
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    objects = ActiveLookupManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ServiceCategory(LookupModel):
    """The kind of work being purchased: New Website, Redesign, Bug Fix,
    Maintenance, ... Packages belong to one of these."""

    class Meta(LookupModel.Meta):
        verbose_name_plural = "service categories"


class WebsiteCategory(LookupModel):
    """The industry/purpose of the resulting website: E-commerce,
    Portfolio, Corporate, Blog, Educational, Non-profit, ..."""

    icon = models.CharField(max_length=50, blank=True, default="")

    class Meta(LookupModel.Meta):
        verbose_name_plural = "website categories"


class WebsiteType(LookupModel):
    """The structural kind of build: Landing Page, Multi-page,
    Web Application, E-commerce Store, ..."""

    class Meta(LookupModel.Meta):
        verbose_name_plural = "website types"


class Technology(LookupModel):
    """Tech-stack tags a Package can advertise (React, WordPress,
    Django, Shopify, ...) — filterable on the Packages API."""

    icon_url = models.URLField(blank=True, default="")


class Tag(LookupModel):
    """Free-form marketing tags on a Package ("popular", "fast-delivery",
    "seo-optimized") — filterable/searchable, distinct from the
    structured Technology list."""

    class Meta(LookupModel.Meta):
        pass


class WebsiteFeature(LookupModel):
    """
    Canonical feature catalog (Contact Form, Blog, Payment Gateway,
    Newsletter Signup, Multi-language, Live Chat, ...). Referenced from
    both sides: PackageFeature (what a package includes) and
    apps.bookings.BookingRequirement (what a customer asked for) — one
    catalog, so "does this package cover what the customer wants" is a
    direct FK comparison rather than fuzzy text matching.
    """

    icon = models.CharField(max_length=50, blank=True, default="")


class PackageQuerySet(SoftDeleteQuerySet):
    def published(self):
        return self.alive().filter(status=Package.Status.PUBLISHED, visibility=Package.Visibility.PUBLIC)


class PackageManager(SoftDeleteManager):
    def get_queryset(self):
        return PackageQuerySet(self.model, using=self._db).alive()

    def published(self):
        return self.get_queryset().published()


class Package(TimeStampedModel, SoftDeleteModel):
    """
    A pricing tier (Basic/Standard/Premium) within a ServiceCategory.
    Integer PK: packages are public listings by nature (anyone can
    browse the full catalog), so there's no enumeration concern that
    would justify a UUID the way there is for a private Booking.
    """

    class Tier(models.TextChoices):
        BASIC = "BASIC", "Basic"
        STANDARD = "STANDARD", "Standard"
        PREMIUM = "PREMIUM", "Premium"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        HIDDEN = "HIDDEN", "Hidden"
        ARCHIVED = "ARCHIVED", "Archived"

    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        UNLISTED = "UNLISTED", "Unlisted"  # visible via direct link, not in listings
        PRIVATE = "PRIVATE", "Private"  # admin/developer only, e.g. a custom quote

    service_category = models.ForeignKey(
        ServiceCategory, on_delete=models.PROTECT, related_name="packages"
    )
    tier = models.CharField(max_length=20, choices=Tier.choices)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField()
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_days = models.PositiveIntegerField()
    revision_count = models.PositiveIntegerField()
    support_duration_days = models.PositiveIntegerField()

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC, db_index=True
    )

    technologies = models.ManyToManyField(Technology, related_name="packages", blank=True)
    tags = models.ManyToManyField(Tag, related_name="packages", blank=True)
    features = models.ManyToManyField(
        WebsiteFeature, through="PackageFeature", related_name="packages"
    )

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="packages_created"
    )
    # "Developer Editable (only where allowed)": nullable — most packages
    # have no developer editor and are admin-only. When set, that one
    # developer may update (not publish/hide/delete) this package's
    # content; see bookings... (catalog).permissions.CanEditPackage.
    developer_editor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="packages_editable",
        limit_choices_to={"role": "DEVELOPER"},
    )

    objects = PackageManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["service_category", "starting_price"]
        indexes = [
            models.Index(fields=["status", "visibility"]),
            models.Index(fields=["service_category", "tier"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["service_category", "tier"],
                condition=models.Q(is_deleted=False),
                name="unique_tier_per_service_category_alive",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"

    def publish(self):
        self.status = Package.Status.PUBLISHED
        self.save(update_fields=["status", "updated_at"])

    def hide(self):
        self.status = Package.Status.HIDDEN
        self.save(update_fields=["status", "updated_at"])


class PackageFeature(models.Model):
    """Through table: which WebsiteFeatures a Package includes, with
    per-package display metadata (highlighted, ordering)."""

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="package_features")
    website_feature = models.ForeignKey(
        WebsiteFeature, on_delete=models.CASCADE, related_name="package_features"
    )
    is_highlighted = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["package", "website_feature"], name="unique_feature_per_package"
            ),
        ]

    def __str__(self):
        return f"{self.package.name} — {self.website_feature.name}"