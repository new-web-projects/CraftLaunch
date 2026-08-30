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
    NotificationEvent,
    ProjectAttachment,
    ProjectDelivery,
    ProjectMilestone,
    ProjectStatus,
    RevisionRequest,
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


class RecentActivitySerializer(serializers.ModelSerializer):
    """Same underlying rows as BookingTimelineSerializer, but for the
    cross-booking "Recent Activity" feed on both dashboards — which
    booking each event belongs to matters there in a way it doesn't on
    a single booking's own timeline tab."""

    actor = PublicUserSummarySerializer(read_only=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    booking_id = serializers.UUIDField(source="booking.id", read_only=True)
    website_name = serializers.CharField(source="booking.website_name", read_only=True)

    class Meta:
        model = BookingTimeline
        fields = [
            "id", "event_type", "event_type_display", "actor",
            "description", "booking_id", "website_name", "created_at",
        ]
        read_only_fields = fields


class BookingNoteSerializer(serializers.ModelSerializer):
    author = PublicUserSummarySerializer(read_only=True)

    class Meta:
        model = BookingNote
        fields = ["id", "author", "content", "is_internal", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class BookingNoteCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/bookings/<uuid>/notes/. `is_internal`
    is accepted but only ever honoured for staff — see the view."""

    content = serializers.CharField(max_length=2000)
    is_internal = serializers.BooleanField(required=False, default=False)


class DeveloperAssignmentSerializer(serializers.ModelSerializer):
    developer = PublicUserSummarySerializer(read_only=True)

    class Meta:
        model = DeveloperAssignment
        fields = ["id", "developer", "role_note", "assigned_at", "is_active"]
        read_only_fields = fields


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    completed_by = PublicUserSummarySerializer(read_only=True)

    class Meta:
        model = ProjectMilestone
        fields = [
            "id", "stage", "stage_display", "sort_order",
            "is_completed", "completed_at", "completed_by",
        ]
        read_only_fields = fields


class ProjectDeliverySerializer(serializers.ModelSerializer):
    delivered_by = PublicUserSummarySerializer(read_only=True)
    files = ProjectAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectDelivery
        fields = [
            "notes", "final_url", "access_instructions", "files",
            "delivered_by", "delivered_at", "accepted_at",
        ]
        read_only_fields = fields


class DeliverySubmitSerializer(serializers.Serializer):
    """Input shape for POST /api/bookings/<uuid>/delivery/ — the
    developer's "submit delivery" form."""

    notes = serializers.CharField(required=False, allow_blank=True)
    final_url = serializers.URLField(required=False, allow_blank=True)
    access_instructions = serializers.CharField(required=False, allow_blank=True)
    attachment_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )


class RevisionRequestSerializer(serializers.ModelSerializer):
    requested_by = PublicUserSummarySerializer(read_only=True)
    attachment = ProjectAttachmentSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RevisionRequest
        fields = [
            "id", "reason", "description", "attachment",
            "status", "status_display", "requested_by", "created_at",
        ]
        read_only_fields = fields


class RevisionRequestCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/bookings/<uuid>/revisions/ — the
    customer's "request a revision" form."""

    reason = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    attachment_id = serializers.UUIDField(required=False, allow_null=True)


class ProjectRejectSerializer(serializers.Serializer):
    """Input shape for POST /api/bookings/<uuid>/reject/."""

    reason = serializers.CharField(max_length=255)


class BookingCancelSerializer(serializers.Serializer):
    """
    Input shape for POST /api/bookings/<uuid>/cancel/. The spec is
    explicit that cancellation must require a reason — enforced here,
    at the API boundary, rather than inside BookingService.cancel()
    itself: that method's `reason` parameter stays optional so it can
    still be called directly (an admin tool, a test) without this
    product-facing requirement following it everywhere. Real
    cancellations, which only ever arrive through this endpoint,
    always carry one.
    """

    reason = serializers.CharField(max_length=500, min_length=5)


class DeveloperActionNoteSerializer(serializers.Serializer):
    """Shared input shape for the light developer actions that only
    ever take an optional free-text note (mark-waiting-for-customer,
    mark-ready)."""

    note = serializers.CharField(required=False, allow_blank=True)


class NotificationEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    booking_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = NotificationEvent
        fields = ["id", "event_type", "event_type_display", "message", "booking_id", "is_read", "created_at"]
        read_only_fields = fields


class ReferenceLinkSerializer(serializers.Serializer):
    label = serializers.CharField(required=False, allow_blank=True, max_length=100)
    url = serializers.URLField()


class BookingListSerializer(serializers.ModelSerializer):
    package = PackageListSerializer(read_only=True)
    website_category = WebsiteCategorySerializer(read_only=True)
    status = ProjectStatusSerializer(read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "website_name", "business_name", "package", "website_category",
            "status", "preferred_delivery_date", "created_at", "progress_percent",
        ]


class BookingDetailSerializer(BookingListSerializer):
    website_type = WebsiteTypeSerializer(read_only=True)
    booking_requirements = BookingRequirementSerializer(many=True, read_only=True)
    customer_requirements = CustomerRequirementSerializer(many=True, read_only=True)
    attachments = ProjectAttachmentSerializer(many=True, read_only=True)
    timeline_events = BookingTimelineSerializer(many=True, read_only=True)
    notes = serializers.SerializerMethodField()
    developer_assignments = DeveloperAssignmentSerializer(many=True, read_only=True)
    milestones = ProjectMilestoneSerializer(many=True, read_only=True)
    delivery = serializers.SerializerMethodField()
    revision_requests = RevisionRequestSerializer(many=True, read_only=True)

    class Meta(BookingListSerializer.Meta):
        fields = BookingListSerializer.Meta.fields + [
            "website_type", "business_type", "description", "reference_links",
            "submitted_at", "booking_requirements", "customer_requirements",
            "attachments", "timeline_events", "notes", "developer_assignments",
            "milestones", "delivery", "revision_requests",
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

    def get_delivery(self, booking):
        try:
            return ProjectDeliverySerializer(booking.delivery).data
        except ProjectDelivery.DoesNotExist:
            return None


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