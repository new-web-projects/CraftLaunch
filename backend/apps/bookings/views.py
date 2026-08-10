from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import IsAdminRole, IsCustomer

from .models import Booking, BookingTimeline, ProjectAttachment
from .permissions import IsBookingOwner, IsBookingParticipant
from .serializers import (
    BookingCreateSerializer,
    BookingDetailSerializer,
    BookingListSerializer,
    BookingTimelineSerializer,
    ProjectAttachmentSerializer,
)
from .services import AttachmentService, BookingService


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
    filterset_fields = ["status__code", "package"]
    ordering_fields = ["created_at", "preferred_delivery_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        base = (
            Booking.objects.select_related("package", "website_category", "status")
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
        )


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated, IsBookingOwner]

    def post(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        self.check_object_permissions(request, booking)
        try:
            BookingService.cancel(booking, actor=request.user, reason=request.data.get("reason", ""))
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