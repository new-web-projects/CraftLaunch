from django.contrib import admin

from .models import (
    Booking,
    BookingNote,
    BookingRequirement,
    BookingTimeline,
    CustomerRequirement,
    DeveloperAssignment,
    ProjectAttachment,
    ProjectStatus,
)


@admin.register(ProjectStatus)
class ProjectStatusAdmin(admin.ModelAdmin):
    list_display = ("label", "code", "sort_order", "is_terminal", "is_default", "color")
    search_fields = ("label", "code")
    ordering = ("sort_order",)


class BookingRequirementInline(admin.TabularInline):
    model = BookingRequirement
    extra = 0
    autocomplete_fields = ["website_feature"]


class CustomerRequirementInline(admin.TabularInline):
    model = CustomerRequirement
    extra = 0


class ProjectAttachmentInline(admin.TabularInline):
    model = ProjectAttachment
    extra = 0
    readonly_fields = ("storage_provider", "storage_key", "original_filename", "file_size", "uploaded_by")
    can_delete = False


class BookingNoteInline(admin.TabularInline):
    model = BookingNote
    extra = 0
    readonly_fields = ("created_at",)


class DeveloperAssignmentInline(admin.TabularInline):
    model = DeveloperAssignment
    extra = 0
    autocomplete_fields = ["developer"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "website_name", "customer", "package", "status", "preferred_delivery_date", "created_at", "is_deleted",
    )
    list_filter = ("status", "business_type", "website_category")
    search_fields = ("website_name", "business_name", "customer__username", "customer__email")
    autocomplete_fields = ["customer", "package", "website_category", "website_type", "status"]
    readonly_fields = ("id", "idempotency_key", "submitted_at", "created_at", "updated_at")
    inlines = [
        BookingRequirementInline,
        CustomerRequirementInline,
        ProjectAttachmentInline,
        DeveloperAssignmentInline,
        BookingNoteInline,
    ]

    def get_queryset(self, request):
        return Booking.all_objects.select_related("customer", "package", "status")


@admin.register(BookingTimeline)
class BookingTimelineAdmin(admin.ModelAdmin):
    list_display = ("booking", "event_type", "actor", "created_at")
    list_filter = ("event_type",)
    readonly_fields = [f.name for f in BookingTimeline._meta.fields]

    def has_add_permission(self, request):
        # Append-only audit trail — created exclusively through
        # BookingService, never hand-entered.
        return False