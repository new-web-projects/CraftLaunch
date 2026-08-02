from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.models import Role


class IsBookingParticipant(BasePermission):
    """
    A booking is visible to: the customer who owns it, any developer
    currently assigned to it, or any admin. Object-level — pair with
    IsAuthenticated at the view level; this only runs once DRF has an
    object to check (retrieve/update/delete), not on list/create.
    """

    message = "You don't have access to this booking."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == Role.ADMIN:
            return True
        if obj.customer_id == user.id:
            return True
        return obj.developer_assignments.filter(developer=user, is_active=True).exists()


class IsBookingOwner(BasePermission):
    """Stricter than IsBookingParticipant: only the owning customer (or
    an admin) may mutate a booking — assigned developers can view but
    not edit the customer's own booking fields."""

    message = "Only the customer who created this booking (or an admin) can modify it."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return user.role == Role.ADMIN or obj.customer_id == user.id