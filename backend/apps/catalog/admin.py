from django.contrib import admin

from .models import Package, PackageFeature, ServiceCategory, Tag, Technology, WebsiteCategory, WebsiteFeature, WebsiteType


class LookupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(LookupAdmin):
    pass


@admin.register(WebsiteCategory)
class WebsiteCategoryAdmin(LookupAdmin):
    list_display = LookupAdmin.list_display + ("icon",)


@admin.register(WebsiteType)
class WebsiteTypeAdmin(LookupAdmin):
    pass


@admin.register(Technology)
class TechnologyAdmin(LookupAdmin):
    list_display = ("name", "slug", "icon_url", "is_active")


@admin.register(Tag)
class TagAdmin(LookupAdmin):
    pass


@admin.register(WebsiteFeature)
class WebsiteFeatureAdmin(LookupAdmin):
    list_display = LookupAdmin.list_display + ("icon",)


class PackageFeatureInline(admin.TabularInline):
    model = PackageFeature
    extra = 1
    autocomplete_fields = ["website_feature"]


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        "name", "service_category", "tier", "status", "visibility", "starting_price", "is_deleted",
    )
    list_filter = ("status", "visibility", "tier", "service_category")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["service_category", "developer_editor", "technologies", "tags"]
    inlines = [PackageFeatureInline]
    actions = ["publish_packages", "hide_packages"]

    def get_queryset(self, request):
        # all_objects, not objects — admins need to see (and undo)
        # soft-deleted packages too.
        return Package.all_objects.select_related("service_category")

    @admin.action(description="Publish selected packages")
    def publish_packages(self, request, queryset):
        from .services import PackageService

        for package in queryset:
            PackageService.publish(package, actor=request.user)

    @admin.action(description="Hide selected packages")
    def hide_packages(self, request, queryset):
        from .services import PackageService

        for package in queryset:
            PackageService.hide(package, actor=request.user)