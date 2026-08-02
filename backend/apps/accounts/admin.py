from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AdminProfile, CustomerProfile, DeveloperProfile, User, UserSession


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_email_verified", "is_active", "is_staff", "created_at")
    list_filter = ("role", "is_email_verified", "is_active", "is_staff")
    search_fields = ("username", "email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "failed_login_attempts", "locked_until")

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("CraftLaunch", {
            "fields": (
                "role",
                "is_email_verified",
                "failed_login_attempts",
                "locked_until",
                "deletion_requested_at",
                "created_at",
                "updated_at",
            )
        }),
    )


class BaseProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "country", "timezone", "language")
    search_fields = ("user__username", "user__email")


@admin.register(CustomerProfile)
class CustomerProfileAdmin(BaseProfileAdmin):
    pass


@admin.register(DeveloperProfile)
class DeveloperProfileAdmin(BaseProfileAdmin):
    pass


@admin.register(AdminProfile)
class AdminProfileAdmin(BaseProfileAdmin):
    pass


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "jti", "ip_address", "created_at", "last_seen_at")
    search_fields = ("user__username", "jti", "ip_address")
    readonly_fields = ("jti", "created_at", "last_seen_at")