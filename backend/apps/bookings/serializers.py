from rest_framework import serializers

from apps.accounts.serializers import PublicUserSummarySerializer
from apps.catalog.models import Package, WebsiteCategory, WebsiteFeature, WebsiteType
from apps.catalog.serializers import (
    PackageListSerializer,
    WebsiteCategorySerializer,
    WebsiteFeatureSerializer,
    WebsiteTypeSerializer,
)

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
from .services import BookingService


class ProjectStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStatus
        fields = ["code", "label", "sort_order", "is_terminal", "color"]


class BookingRequirementSerializer(serializers.ModelSerializer):
    feature = WebsiteFeatureSerializer(source="website_feature", read_only=True)

    class Meta:
        model = BookingRequirement
        fields = ["feature", "notes"]


class CustomerRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRequirement
        fields = ["id", "title", "description", "priority", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProjectAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = PublicUserSummarySerializer(read_only=True)

    class Meta:
        model = ProjectAttachment
        fields = [
            "id", "original_filename", "content_type", "file_category",
            "file_size", "uploaded_by", "created_at",
        ]
        read_only_fields = fields


class BookingTimelineSerializer(serializers.ModelSerializer):
    actor = PublicUserSummarySerializer(read_only=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    from_status = ProjectStatusSerializer(read_only=True)
    to_status = ProjectStatusSerializer(read_only=True)

    class Meta:
        model = BookingTimeline
        fields = [
            "id", "event_type", "event_type_display", "actor",
            "from_status", "to_status", "description", "created_at",
        ]
        read_only_fields = fields


class BookingNoteSerializer(serializers.ModelSerializer):
    author = PublicUserSummarySerializer(read_only=True)

    class Meta:
        model = BookingNote
        fields = ["id", "author", "content", "is_internal", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class DeveloperAssignmentSerializer(serializers.ModelSerializer):
    developer = PublicUserSummarySerializer(read_only=True)

    class Meta:
        model = DeveloperAssignment
        fields = ["id", "developer", "role_note", "assigned_at", "is_active"]
        read_only_fields = fields


class ReferenceLinkSerializer(serializers.Serializer):
    label = serializers.CharField(required=False, allow_blank=True, max_length=100)
    url = serializers.URLField()


class BookingListSerializer(serializers.ModelSerializer):
    package = PackageListSerializer(read_only=True)
    website_category = WebsiteCategorySerializer(read_only=True)
    status = ProjectStatusSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "website_name", "business_name", "package", "website_category",
            "status", "preferred_delivery_date", "created_at",
        ]


class BookingDetailSerializer(BookingListSerializer):
    website_type = WebsiteTypeSerializer(read_only=True)
    booking_requirements = BookingRequirementSerializer(many=True, read_only=True)
    customer_requirements = CustomerRequirementSerializer(many=True, read_only=True)
    attachments = ProjectAttachmentSerializer(many=True, read_only=True)
    timeline_events = BookingTimelineSerializer(many=True, read_only=True)
    notes = serializers.SerializerMethodField()
    developer_assignments = DeveloperAssignmentSerializer(many=True, read_only=True)

    class Meta(BookingListSerializer.Meta):
        fields = BookingListSerializer.Meta.fields + [
            "website_type", "business_type", "description", "reference_links",
            "submitted_at", "booking_requirements", "customer_requirements",
            "attachments", "timeline_events", "notes", "developer_assignments",
        ]

    def get_notes(self, booking):
        """Internal notes are stripped for anyone who isn't staff —
        the same object serializer is reused for the customer-facing
        and admin/developer-facing responses, so this is where that
        split actually happens."""
        request = self.context.get("request")
        qs = booking.notes.all()
        if not (request and request.user.is_authenticated and request.user.is_staff):
            qs = qs.filter(is_internal=False)
        return BookingNoteSerializer(qs, many=True).data


class CustomerRequirementInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=CustomerRequirement.Priority.choices, required=False)


class BookingCreateSerializer(serializers.Serializer):
    """
    Write-only input shape for POST /api/bookings/. Delegates the
    actual creation to BookingService so the same validated business
    rules apply whether a booking is created from this endpoint, a
    future admin action, or a management command.
    """

    package = serializers.PrimaryKeyRelatedField(queryset=Package.objects.published())
    website_category = serializers.PrimaryKeyRelatedField(queryset=WebsiteCategory.objects.active())
    website_type = serializers.PrimaryKeyRelatedField(
        queryset=WebsiteType.objects.active(), required=False, allow_null=True
    )
    website_name = serializers.CharField(max_length=150)
    business_name = serializers.CharField(max_length=150)
    business_type = serializers.ChoiceField(choices=Booking.BusinessType.choices)
    description = serializers.CharField()
    preferred_delivery_date = serializers.DateField(required=False, allow_null=True)
    reference_links = ReferenceLinkSerializer(many=True, required=False)
    required_feature_ids = serializers.PrimaryKeyRelatedField(
        source="required_features",
        queryset=WebsiteFeature.objects.active(),
        many=True,
        required=False,
    )
    custom_requirements = CustomerRequirementInputSerializer(many=True, required=False)

    def create(self, validated_data):
        request = self.context["request"]
        return BookingService.create_booking(
            customer=request.user,
            package=validated_data["package"],
            website_category=validated_data["website_category"],
            website_type=validated_data.get("website_type"),
            website_name=validated_data["website_name"],
            business_name=validated_data["business_name"],
            business_type=validated_data["business_type"],
            description=validated_data["description"],
            preferred_delivery_date=validated_data.get("preferred_delivery_date"),
            reference_links=validated_data.get("reference_links"),
            required_feature_ids=[f.id for f in validated_data.get("required_features", [])],
            custom_requirements=validated_data.get("custom_requirements"),
            idempotency_key=request.headers.get("Idempotency-Key"),
        )