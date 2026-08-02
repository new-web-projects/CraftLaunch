"""
Business logic that doesn't belong on a serializer or directly on a
model method — kept callable from both the API views and (later)
Django admin actions or management commands without duplicating logic
in either place.

"Repository" layer note: this project uses Django's own Manager/
QuerySet (see ActiveLookupManager, PackageManager in models.py) as the
repository/data-access abstraction rather than a separate parallel
class per model — Django's ORM already *is* that abstraction, and a
second layer wrapping `Package.objects.filter(...)` calls would mostly
just rename methods without adding real value. Services here call
managers directly; nothing above the service layer talks to the ORM.
"""

from django.db import transaction

from .models import Package


class PackageService:
    @staticmethod
    @transaction.atomic
    def publish(package: Package, *, actor) -> Package:
        # `actor` isn't persisted anywhere yet — no dedicated audit-log
        # model exists for catalog changes in this part (Package's own
        # created_by/updated_at are the only trail today). Kept as a
        # required kwarg now so adding real audit logging later is a
        # change inside this method, not a signature change across
        # every call site.
        package.publish()
        return package

    @staticmethod
    @transaction.atomic
    def hide(package: Package, *, actor) -> Package:
        package.hide()
        return package

    @staticmethod
    @transaction.atomic
    def delete(package: Package, *, actor) -> None:
        package.soft_delete()