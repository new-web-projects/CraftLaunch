from rest_framework.permissions import BasePermission

from .models import Role


class IsCustomer(BasePermission):
    message = "This action is restricted to customer accounts."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.CUSTOMER)


class IsDeveloper(BasePermission):
    message = "This action is restricted to developer accounts."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.DEVELOPER)


class IsAdminRole(BasePermission):
    message = "This action is restricted to admin accounts."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.ADMIN)


class IsSuperAdmin(BasePermission):
    """
    Stricter than IsAdminRole: Django's own is_superuser flag, not the
    `role` field. Only a Super Admin (bootstrapped via
    `createsuperuser`, or promoted directly in Django admin) can create
    further Admin accounts — see AdminRegisterSerializer.
    """

    message = "This action requires super admin privileges."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)