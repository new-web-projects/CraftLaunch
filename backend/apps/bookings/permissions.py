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


class IsAssignedDeveloper(BasePermission):
    """
    Part 5: stricter than IsBookingParticipant for actions a developer
    performs *on a project they're actually assigned to* (start work,
    update milestones, submit delivery) — being able to *view* a
    booking (IsBookingParticipant) is not the same as being allowed to
    act on it. An admin may still act on any project; any OTHER
    developer (including one merely browsing open requests) may not,
    satisfying the spec's "do not allow unauthorized developers to
    ... another developer's project" for every action past acceptance,
    not just acceptance itself.
    """

    message = "You're not the developer assigned to this project."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == Role.ADMIN:
            return True
        return obj.developer_assignments.filter(developer=user, is_active=True).exists()