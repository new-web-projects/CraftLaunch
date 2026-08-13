"""
Abstract base models shared by apps/catalog and apps/bookings.

Deliberately its own app rather than living inside catalog or bookings:
both of those apps need these mixins, and having one "own" them would
create an artificial dependency direction. No concrete models here, so
no migrations for this app either — abstract models don't create
tables themselves.
"""

import uuid

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """created_at/updated_at, timezone-aware (USE_TZ=True project-wide
    since Part 1) and set automatically."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    UUID primary key. Used for models that get exposed in customer-
    facing URLs or external references (Booking and everything hanging
    off it) — non-guessable, no enumeration risk, and safe to reference
    before a row is committed (e.g. generating an upload path ahead of
    the attachment record being saved). Catalog lookup tables
    (categories, tags, technologies, ...) intentionally keep plain
    integer PKs instead: they're admin-managed, not sensitive, and an
    incrementing id is simpler to work with in the Django admin and in
    ordering/filtering.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SingletonModel(models.Model):
    """
    Exactly one row, always at pk=1. For Part 4's configuration models
    (SiteConfiguration, SEOConfiguration, ...): there's one active
    website configuration, not one per admin or per request, so a
    normal table (insert new rows, query the "latest" or "active" one)
    is the wrong shape — it invites a second row existing by accident
    and code reading whichever one it happens to fetch first.

    `load()` is the only supported way to get the instance: it
    get-or-creates pk=1, so callers never handle "no configuration
    row yet" as a special case — a fresh database still returns a
    valid instance with the model's field defaults. `save()` forces
    pk=1 regardless of what's set on the instance, and `delete()` is a
    no-op — the row that every settings read depends on shouldn't be
    deletable through the ORM's normal path.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)

    def delete(self):
        """Bulk queryset .delete() soft-deletes instead of removing rows."""
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Default manager — `Model.objects` only ever sees non-deleted
    rows, matching what "soft delete" is supposed to mean everywhere
    a queryset is built from `objects` without extra effort."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """
    `objects` (the default manager) excludes soft-deleted rows;
    `all_objects` sees everything, for admin/reporting use. A model
    using this mixin should not also define its own `objects` manager
    without composing this one in — see catalog/managers.py and
    bookings/managers.py for how the two get combined.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])