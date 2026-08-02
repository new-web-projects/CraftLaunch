from rest_framework import serializers

from .models import (
    Package,
    PackageFeature,
    ServiceCategory,
    Tag,
    Technology,
    WebsiteCategory,
    WebsiteFeature,
    WebsiteType,
)


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "slug", "description", "sort_order"]


class WebsiteCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteCategory
        fields = ["id", "name", "slug", "description", "icon", "sort_order"]


class WebsiteTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteType
        fields = ["id", "name", "slug", "description", "sort_order"]


class TechnologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Technology
        fields = ["id", "name", "slug", "icon_url"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class WebsiteFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteFeature
        fields = ["id", "name", "slug", "description", "icon"]


class PackageFeatureSerializer(serializers.ModelSerializer):
    feature = WebsiteFeatureSerializer(source="website_feature", read_only=True)

    class Meta:
        model = PackageFeature
        fields = ["feature", "is_highlighted", "sort_order"]


class PackageListSerializer(serializers.ModelSerializer):
    """Lighter shape for GET /api/catalog/packages/ — full feature list
    and description are left to the detail endpoint."""

    service_category = ServiceCategorySerializer(read_only=True)
    tier_display = serializers.CharField(source="get_tier_display", read_only=True)
    technologies = TechnologySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Package
        fields = [
            "id", "slug", "name", "tier", "tier_display", "service_category",
            "starting_price", "delivery_days", "revision_count",
            "technologies", "tags",
        ]


class PackageDetailSerializer(PackageListSerializer):
    package_features = PackageFeatureSerializer(many=True, read_only=True)

    class Meta(PackageListSerializer.Meta):
        fields = PackageListSerializer.Meta.fields + [
            "description", "support_duration_days", "package_features", "status", "visibility",
        ]


class PackageWriteSerializer(serializers.ModelSerializer):
    """Admin create/update. Publish/hide/delete go through
    catalog/services.py::PackageService instead of a PATCH to `status`
    directly, so those actions get their own timeline/permission story
    rather than being just another field write."""

    class Meta:
        model = Package
        fields = [
            "id", "service_category", "tier", "name", "slug", "description",
            "starting_price", "delivery_days", "revision_count", "support_duration_days",
            "visibility", "technologies", "tags", "developer_editor",
        ]
        read_only_fields = ["id"]

    def validate_starting_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Starting price must be greater than zero.")
        return value

    def validate(self, attrs):
        # Mirrors the DB-level UniqueConstraint
        # (unique_tier_per_service_category_alive in models.py) at the
        # serializer level, so a duplicate returns a clean 400 instead
        # of an unhandled IntegrityError.
        service_category = attrs.get("service_category", getattr(self.instance, "service_category", None))
        tier = attrs.get("tier", getattr(self.instance, "tier", None))
        if service_category and tier:
            qs = Package.all_objects.filter(
                service_category=service_category, tier=tier, is_deleted=False
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"tier": f"A {tier.title()} package already exists for this service category."}
                )
        return attrs