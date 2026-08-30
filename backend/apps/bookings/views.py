from django.core.exceptions import ValidationError as DjangoValidationError
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import IsCustomer, IsDeveloper

from .models import (
    Booking,
    BookingTimeline,
    NotificationEvent,
    ProjectAttachment,
    ProjectDelivery,
    ProjectMilestone,
)
from .permissions import IsAssignedDeveloper, IsBookingOwner, IsBookingParticipant
from .serializers import (
    BookingCancelSerializer,
    BookingCreateSerializer,
    BookingDetailSerializer,
    BookingListSerializer,
    BookingNoteCreateSerializer,
    BookingNoteSerializer,
    BookingTimelineSerializer,
    CustomerRequirementInputSerializer,
    CustomerRequirementSerializer,
    DeliverySubmitSerializer,
    DeveloperActionNoteSerializer,
    NotificationEventSerializer,
    ProjectAttachmentSerializer,
    ProjectDeliverySerializer,
    ProjectMilestoneSerializer,
    ProjectRejectSerializer,
    RecentActivitySerializer,
    RevisionRequestCreateSerializer,
    RevisionRequestSerializer,
)
from .services import AttachmentService, BookingService, DeliveryService, MilestoneService, ProjectLifecycleService, RevisionService

# Non-terminal, "still moving" statuses — used to build the dashboard
# bucket queries below. Kept here (not in lifecycle.py) since these
# groupings are a dashboard/reporting concern, not part of the state
# machine's own rules.
ACTIVE_STATUS_CODES = [
    "accepted", "in_progress", "waiting_for_customer", "revision_requested", "ready_for_delivery",
]
PENDING_STATUS_CODES = ["draft", "submitted", "awaiting_developer"]
CANCELLED_LIKE_STATUS_CODES = ["cancelled", "rejected"]
AWAITING_CUSTOMER_ACTION_CODES = ["waiting_for_customer", "delivered"]


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    """Comma-separated multi-value filter, e.g. ?status=in_progress,
    waiting_for_customer — used by the dashboard's stat-card links and
    the nav's "Active Projects"/"My Projects" style shortcuts, which
    all need an OR-of-several-statuses filter, not just one exact
    match."""


class BookingFilterSet(django_filters.FilterSet):
    status = CharInFilter(field_name="status__code")

    class Meta:
        model = Booking
        fields = ["status", "package"]


def _django_validation_to_drf(exc: DjangoValidationError) -> DRFValidationError:
    return DRFValidationError({"detail": exc.messages if hasattr(exc, "messages") else str(exc)})


class BookingListCreateView(generics.ListCreateAPIView):
    """
    GET: role-scoped list — a customer sees their own bookings, a
    developer sees bookings they're assigned to, an admin sees
    everything. POST: customer-only (a developer/admin creating a
    booking on a customer's behalf is out of scope for this part).

    Pagination/filtering/sorting-ready: ?status=<code>,
    ?ordering=-created_at / preferred_delivery_date.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = BookingFilterSet
    ordering_fields = ["created_at", "preferred_delivery_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        base = Booking.objects.select_related("package", "website_category", "status").prefetch_related(
            "milestones"
        )
        if user.role == Role.ADMIN:
            return base.all()
        if user.role == Role.DEVELOPER:
            return base.for_developer(user)
        return base.for_customer(user)

    def get_serializer_class(self):
        return BookingCreateSerializer if self.request.method == "POST" else BookingListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsCustomer()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = serializer.save()
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/bookings/<uuid>/ — visible to the owning
    customer, an assigned developer, or an admin; mutable only by the
    owning customer or an admin (IsBookingOwner)."""

    permission_classes = [IsAuthenticated, IsBookingParticipant, IsBookingOwner]
    serializer_class = BookingDetailSerializer

    def get_queryset(self):
        return Booking.objects.for_user(self.request.user).select_related(
            "package__service_category", "website_category", "website_type", "status"
        ).prefetch_related(
            "booking_requirements__website_feature",
            "customer_requirements",
            "attachments__uploaded_by",
            "timeline_events__actor",
            "timeline_events__from_status",
            "timeline_events__to_status",
            "notes__author",
            "developer_assignments__developer",
            "milestones__completed_by",
            "revision_requests__requested_by",
            "revision_requests__attachment",
            "delivery__files",
            "delivery__delivered_by",
        )


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated, IsBookingOwner]

    def post(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            BookingService.cancel(booking, actor=request.user, reason=serializer.validated_data["reason"])
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class BookingTimelineView(generics.ListAPIView):
    """GET /api/bookings/<uuid>/timeline/ — dedicated, paginated
    endpoint (separate from the nested list on BookingDetailView) so a
    long-running booking's full history doesn't have to be paged
    through the booking detail response."""

    permission_classes = [IsAuthenticated, IsBookingParticipant]
    serializer_class = BookingTimelineSerializer

    def get_queryset(self):
        booking = generics.get_object_or_404(Booking.objects.for_user(self.request.user), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, booking)
        return booking.timeline_events.select_related("actor", "from_status", "to_status")


class AttachmentUploadView(APIView):
    """POST /api/bookings/<uuid>/attachments/ — multipart file upload."""

    permission_classes = [IsAuthenticated, IsBookingParticipant]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)

        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attachment = AttachmentService.upload(
                booking,
                uploaded_by=request.user,
                file=upload,
                filename=upload.name,
                content_type=upload.content_type or "application/octet-stream",
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)

        return Response(ProjectAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)


class AttachmentDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsBookingParticipant]

    def delete(self, request, pk, attachment_id):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)
        attachment = generics.get_object_or_404(
            ProjectAttachment.objects, pk=attachment_id, booking=booking
        )
        AttachmentService.delete(attachment, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================================
# Part 5 — dashboards
# =====================================================================


class CustomerDashboardView(APIView):
    """GET /api/bookings/dashboard/customer/ — every number and list
    is computed from the customer's own bookings only; there is no ID
    parameter anywhere on this endpoint, so there's no URL a customer
    could edit to see anyone else's dashboard."""

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        user = request.user
        qs = Booking.objects.for_customer(user).select_related("package", "website_category", "status")

        counts = {
            "active_projects": qs.filter(status__code__in=ACTIVE_STATUS_CODES).count(),
            "pending_bookings": qs.filter(status__code__in=PENDING_STATUS_CODES).count(),
            "completed_projects": qs.filter(status__code="completed").count(),
            "cancelled_projects": qs.filter(status__code__in=CANCELLED_LIKE_STATUS_CODES).count(),
            "awaiting_your_action": qs.filter(status__code__in=AWAITING_CUSTOMER_ACTION_CODES).count(),
        }
        recently_updated = qs.prefetch_related("milestones").order_by("-updated_at")[:5]
        recent_activity = (
            BookingTimeline.objects.filter(booking__customer=user)
            .select_related("actor", "booking")
            .order_by("-created_at")[:10]
        )

        return Response(
            {
                "counts": counts,
                "recently_updated": BookingListSerializer(recently_updated, many=True).data,
                "recent_activity": RecentActivitySerializer(recent_activity, many=True).data,
            }
        )


class DeveloperDashboardView(APIView):
    """GET /api/bookings/dashboard/developer/ — same no-ID-parameter
    shape as CustomerDashboardView. `new_project_requests` is the one
    number here that is deliberately NOT scoped to `user`: it's the
    size of the shared, unclaimed request pool every developer sees on
    the "Project Requests" page, not something owned by any one
    developer."""

    permission_classes = [IsAuthenticated, IsDeveloper]

    def get(self, request):
        user = request.user
        qs = Booking.objects.for_developer(user).select_related("package", "website_category", "status")

        counts = {
            "new_project_requests": Booking.objects.filter(status__code="awaiting_developer").count(),
            "accepted_projects": qs.filter(status__code="accepted").count(),
            "active_projects": qs.filter(status__code="in_progress").count(),
            "waiting_for_customer": qs.filter(status__code="waiting_for_customer").count(),
            "ready_for_delivery": qs.filter(status__code="ready_for_delivery").count(),
            "completed_projects": qs.filter(status__code="completed").count(),
            "cancelled_projects": qs.filter(status__code__in=CANCELLED_LIKE_STATUS_CODES).count(),
        }
        upcoming_deadlines = (
            qs.prefetch_related("milestones")
            .exclude(status__code__in=CANCELLED_LIKE_STATUS_CODES + ["completed"])
            .filter(preferred_delivery_date__isnull=False)
            .order_by("preferred_delivery_date")[:5]
        )
        recent_activity = (
            BookingTimeline.objects.filter(
                booking__developer_assignments__developer=user,
                booking__developer_assignments__is_active=True,
            )
            .select_related("actor", "booking")
            .distinct()
            .order_by("-created_at")[:10]
        )

        return Response(
            {
                "counts": counts,
                "upcoming_deadlines": BookingListSerializer(upcoming_deadlines, many=True).data,
                "recent_activity": RecentActivitySerializer(recent_activity, many=True).data,
            }
        )


# =====================================================================
# Part 5 — developer project requests (accept / reject)
# =====================================================================


class DeveloperProjectRequestListView(generics.ListAPIView):
    """GET /api/bookings/requests/ — every booking currently open for
    any developer to accept. Deliberately not for_user()-scoped: this
    is the shared pool, the same for every developer account, not
    private data — visibility here is about status, not ownership."""

    permission_classes = [IsAuthenticated, IsDeveloper]
    serializer_class = BookingDetailSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "preferred_delivery_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Booking.objects.filter(status__code="awaiting_developer")
            .exclude(developer_assignments__is_active=True)
            .select_related("package__service_category", "website_category", "website_type", "status")
            .prefetch_related(
                "booking_requirements__website_feature",
                "customer_requirements",
                "attachments__uploaded_by",
            )
        )


class ProjectAcceptView(APIView):
    """POST /api/bookings/<uuid>/accept/ — see
    ProjectLifecycleService.accept_project for the concurrency-safety
    note; two developers hitting this for the same booking at once is
    exactly what that lock exists for."""

    permission_classes = [IsAuthenticated, IsDeveloper]

    def post(self, request, pk):
        generics.get_object_or_404(Booking.objects.filter(status__code="awaiting_developer"), pk=pk)
        try:
            booking = ProjectLifecycleService.accept_project(pk, developer=request.user)
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class ProjectRejectView(APIView):
    permission_classes = [IsAuthenticated, IsDeveloper]

    def post(self, request, pk):
        generics.get_object_or_404(Booking.objects.filter(status__code="awaiting_developer"), pk=pk)
        serializer = ProjectRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = ProjectLifecycleService.reject_project(
                pk, developer=request.user, reason=serializer.validated_data["reason"]
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


# =====================================================================
# Part 5 — assigned-developer project management
# =====================================================================


class _AssignedDeveloperActionView(APIView):
    """Shared lookup for the handful of actions only the developer
    actually assigned to a project (or an admin) may perform. Uses the
    unscoped manager for the initial fetch — IsAssignedDeveloper's
    object-level check is what actually decides access, not queryset
    membership — so a developer who is NOT assigned still gets a clear
    403 rather than a 404 that would incorrectly suggest the project
    doesn't exist."""

    permission_classes = [IsAuthenticated, IsAssignedDeveloper]

    def get_booking(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.all(), pk=pk)
        self.check_object_permissions(request, booking)
        return booking


class ProjectStartView(_AssignedDeveloperActionView):
    def post(self, request, pk):
        booking = self.get_booking(request, pk)
        try:
            booking = ProjectLifecycleService.start_project(booking, developer=request.user)
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class ProjectMarkWaitingForCustomerView(_AssignedDeveloperActionView):
    def post(self, request, pk):
        booking = self.get_booking(request, pk)
        serializer = DeveloperActionNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = ProjectLifecycleService.mark_waiting_for_customer(
                booking, developer=request.user, note=serializer.validated_data.get("note", "")
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class ProjectMarkReadyView(_AssignedDeveloperActionView):
    def post(self, request, pk):
        booking = self.get_booking(request, pk)
        serializer = DeveloperActionNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = ProjectLifecycleService.mark_ready_for_delivery(
                booking, developer=request.user, note=serializer.validated_data.get("note", "")
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


# =====================================================================
# Part 5 — milestones
# =====================================================================


class MilestoneListView(generics.ListAPIView):
    # A booking has at most 6 milestones (ProjectMilestone.DEFAULT_STAGES)
    # — wrapping that in a paginated {count, next, previous, results}
    # envelope adds nothing and doesn't match what a plain milestone
    # checklist needs, unlike the booking list itself.
    pagination_class = None
    permission_classes = [IsAuthenticated, IsBookingParticipant]
    serializer_class = ProjectMilestoneSerializer

    def get_queryset(self):
        booking = generics.get_object_or_404(Booking.objects.for_user(self.request.user), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, booking)
        return booking.milestones.select_related("completed_by")


class MilestoneUpdateView(_AssignedDeveloperActionView):
    """PATCH /api/bookings/<uuid>/milestones/<id>/ with
    {"is_completed": true|false} — the only two writable states; a
    milestone is never renamed, reordered, or deleted through the API,
    only marked done or reopened."""

    def patch(self, request, pk, milestone_id):
        booking = self.get_booking(request, pk)
        milestone = generics.get_object_or_404(ProjectMilestone, pk=milestone_id, booking=booking)

        is_completed = request.data.get("is_completed")
        if is_completed is None:
            return Response({"detail": '"is_completed" is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if is_completed:
            milestone = MilestoneService.complete_milestone(milestone, actor=request.user)
        else:
            milestone = MilestoneService.reopen_milestone(milestone, actor=request.user)

        return Response(ProjectMilestoneSerializer(milestone).data, status=status.HTTP_200_OK)


# =====================================================================
# Part 5 — delivery
# =====================================================================


class DeliveryView(APIView):
    """GET: any participant may view the current delivery. POST: only
    the assigned developer (or admin) may submit/replace it."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAssignedDeveloper()]
        return [IsAuthenticated(), IsBookingParticipant()]

    def get(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)
        try:
            return Response(ProjectDeliverySerializer(booking.delivery).data)
        except ProjectDelivery.DoesNotExist:
            return Response(None)

    def post(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.all(), pk=pk)
        self.check_object_permissions(request, booking)

        serializer = DeliverySubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            delivery = DeliveryService.submit_delivery(
                booking,
                developer=request.user,
                notes=data.get("notes", ""),
                final_url=data.get("final_url", ""),
                access_instructions=data.get("access_instructions", ""),
                attachment_ids=[str(a) for a in data.get("attachment_ids", [])],
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(ProjectDeliverySerializer(delivery).data, status=status.HTTP_200_OK)


class DeliveryAcceptView(APIView):
    """POST /api/bookings/<uuid>/delivery/accept/ — customer (or
    admin) only; IsBookingOwner already encodes exactly that rule."""

    permission_classes = [IsAuthenticated, IsBookingOwner]

    def post(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)
        try:
            booking = DeliveryService.accept_delivery(booking, customer=request.user)
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


# =====================================================================
# Part 5 — revisions
# =====================================================================


class RevisionRequestListCreateView(APIView):
    """GET: any participant. POST: customer (or admin) only —
    IsBookingOwner again."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsBookingOwner()]
        return [IsAuthenticated(), IsBookingParticipant()]

    def get(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)
        qs = booking.revision_requests.select_related("requested_by", "attachment")
        return Response(RevisionRequestSerializer(qs, many=True).data)

    def post(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)

        serializer = RevisionRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            revision = RevisionService.request_revision(
                booking,
                customer=request.user,
                reason=data["reason"],
                description=data.get("description", ""),
                attachment_id=data.get("attachment_id"),
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(RevisionRequestSerializer(revision).data, status=status.HTTP_201_CREATED)


# =====================================================================
# Part 5 — notifications (event foundation; see NotificationEvent)
# =====================================================================


class NotificationListView(generics.ListAPIView):
    """GET /api/bookings/notifications/ — always scoped to the
    requesting user as recipient; there is no ID parameter, so there's
    no way to request anyone else's notifications."""

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationEventSerializer

    def get_queryset(self):
        return NotificationEvent.objects.filter(recipient=self.request.user)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = generics.get_object_or_404(
            NotificationEvent, pk=notification_id, recipient=request.user
        )
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(NotificationEventSerializer(notification).data)


# =====================================================================
# Part 5 — notes and requirements. Both were already fully built at
# the service/model/serializer layer (BookingService.add_note existed
# since Part 3; CustomerRequirementInputSerializer already backed
# booking creation) but had no endpoint exposing them — this is that
# endpoint, for "Add project notes" (developer) / "Update allowed
# requirements" (customer) and the "Requirements updated" timeline
# event, all explicitly listed in the spec.
# =====================================================================


class BookingNoteListCreateView(APIView):
    """GET: any participant, internal notes filtered out for non-staff
    (BookingDetailSerializer.get_notes already does this same split —
    this endpoint exists for paging a long note history without
    re-fetching the whole booking). POST: any participant may add a
    customer-facing note; only staff may mark one internal."""

    permission_classes = [IsAuthenticated, IsBookingParticipant]

    def get(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)
        qs = booking.notes.select_related("author")
        if not request.user.is_staff:
            qs = qs.filter(is_internal=False)
        return Response(BookingNoteSerializer(qs, many=True).data)

    def post(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)

        serializer = BookingNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        note = BookingService.add_note(
            booking,
            author=request.user,
            content=data["content"],
            is_internal=data.get("is_internal", False) and request.user.is_staff,
        )
        return Response(BookingNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class BookingRequirementListCreateView(APIView):
    """GET/POST /api/bookings/<uuid>/requirements/ — the customer's
    free-text CustomerRequirement list (distinct from the fixed
    catalog-backed BookingRequirement/WebsiteFeature list set at
    booking creation). POST is owner-or-admin, matching every other
    customer-initiated write in this app."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsBookingOwner()]
        return [IsAuthenticated(), IsBookingParticipant()]

    def get(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)
        return Response(CustomerRequirementSerializer(booking.customer_requirements.all(), many=True).data)

    def post(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)

        serializer = CustomerRequirementInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            requirement = BookingService.add_requirement(
                booking,
                actor=request.user,
                title=data["title"],
                description=data.get("description", ""),
                priority=data.get("priority"),
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(CustomerRequirementSerializer(requirement).data, status=status.HTTP_201_CREATED)