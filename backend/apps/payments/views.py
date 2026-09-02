from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import filters, generics, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole, IsCustomer
from apps.bookings.models import Booking

from .models import Payment
from .serializers import (
    AdminPaymentSerializer,
    PaymentHistoryItemSerializer,
    PaymentOrderResponseSerializer,
    PaymentSerializer,
    PaymentVerifySerializer,
    ProjectPaymentSummarySerializer,
)
from .services import PaymentCalculationService, PaymentOrderService, PaymentVerificationService, WebhookService


def _django_validation_to_drf(exc: DjangoValidationError) -> DRFValidationError:
    return DRFValidationError({"detail": exc.messages if hasattr(exc, "messages") else str(exc)})


class PaymentActionThrottle(SimpleRateThrottle):
    """Order creation and verification hit Razorpay's API and touch
    money — worth a tighter, dedicated rate independent of the global
    anon/user throttle, the same reasoning behind
    apps.accounts.throttling.LoginRateThrottle. Keyed by user, since
    every endpoint this applies to requires authentication."""

    scope = "payment_action"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def _get_booking_for_customer(request, pk):
    return generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)


class PaymentOrderCreateView(APIView):
    """POST /api/payments/bookings/<uuid>/{advance,final}/order/ — the
    `phase` class attribute is set per concrete subclass below; both
    share every check via PaymentOrderService.create_order, so the
    validation logic exists exactly once."""

    permission_classes = [IsAuthenticated, IsCustomer]
    throttle_classes = [PaymentActionThrottle]
    phase: str = ""

    def post(self, request, pk):
        booking = _get_booking_for_customer(request, pk)
        try:
            order = PaymentOrderService.create_order(booking, phase=self.phase, customer=request.user)
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(PaymentOrderResponseSerializer(order).data, status=status.HTTP_201_CREATED)


class AdvancePaymentOrderCreateView(PaymentOrderCreateView):
    phase = Payment.Phase.ADVANCE_PAYMENT


class FinalPaymentOrderCreateView(PaymentOrderCreateView):
    phase = Payment.Phase.FINAL_PAYMENT


class PaymentVerifyView(APIView):
    """POST /api/payments/bookings/<uuid>/{advance,final}/verify/ —
    the only path by which a Payment can reach CAPTURED from a
    frontend-initiated request. See
    PaymentVerificationService.verify_payment for the actual checks;
    this view's job is just auth/lookup/serialization around it."""

    permission_classes = [IsAuthenticated, IsCustomer]
    throttle_classes = [PaymentActionThrottle]
    phase: str = ""

    def post(self, request, pk):
        booking = _get_booking_for_customer(request, pk)
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        payment = generics.get_object_or_404(Payment, booking=booking, phase=self.phase)
        payment_order = payment.orders.filter(razorpay_order_id=data["razorpay_order_id"]).first()
        if payment_order is None:
            return Response({"detail": "Payment order not found for this booking."}, status=status.HTTP_404_NOT_FOUND)

        try:
            PaymentVerificationService.verify_payment(
                payment_order.id,
                razorpay_order_id=data["razorpay_order_id"],
                razorpay_payment_id=data["razorpay_payment_id"],
                razorpay_signature=data["razorpay_signature"],
                customer=request.user,
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)

        payment.refresh_from_db()
        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)


class AdvancePaymentVerifyView(PaymentVerifyView):
    phase = Payment.Phase.ADVANCE_PAYMENT


class FinalPaymentVerifyView(PaymentVerifyView):
    phase = Payment.Phase.FINAL_PAYMENT


class PaymentStatusView(APIView):
    """GET /api/payments/bookings/<uuid>/{advance,final}/status/ —
    lightweight polling target for 'payment completed but frontend
    disconnected' / 'verification response delayed': the frontend can
    hit this on a timer without re-running the full summary
    calculation. Booking.objects.for_user() already scopes correctly
    (customer's own bookings, developer's assigned ones, everything
    for admin) — see ProjectPaymentSummaryView's docstring for why
    that's sufficient without a separate object-permission check."""

    permission_classes = [IsAuthenticated]
    phase: str = ""

    def get(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        payment = Payment.objects.filter(booking=booking, phase=self.phase).first()
        if payment is None:
            return Response(None, status=status.HTTP_200_OK)
        return Response(PaymentSerializer(payment).data)


class AdvancePaymentStatusView(PaymentStatusView):
    phase = Payment.Phase.ADVANCE_PAYMENT


class FinalPaymentStatusView(PaymentStatusView):
    phase = Payment.Phase.FINAL_PAYMENT


class ProjectPaymentSummaryView(APIView):
    """GET /api/payments/bookings/<uuid>/summary/ — the one response
    the payment summary / advance / final pages actually render from.
    Every number in it comes straight from
    PaymentCalculationService.get_project_summary(); nothing here is
    computed in this view or expected to be recomputed by the
    frontend.

    Booking.objects.for_user() already returns exactly the right set
    for read access — a customer's own bookings, a developer's
    assigned ones, or everything for an admin — so there's no separate
    object-permission check layered on top here; it would just repeat
    the same scoping for_user() already enforces.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        booking = generics.get_object_or_404(Booking.objects.for_user(request.user), pk=pk)
        summary = PaymentCalculationService.get_project_summary(booking)
        return Response(ProjectPaymentSummarySerializer(summary).data)


class PaymentHistoryView(generics.ListAPIView):
    """GET /api/payments/history/ — every payment across every
    booking the requesting customer has ever made. Scoped strictly to
    request.user with no ID parameter anywhere on this endpoint, so
    there's no URL a customer could edit to see anyone else's
    payments."""

    permission_classes = [IsAuthenticated, IsCustomer]
    serializer_class = PaymentHistoryItemSerializer

    def get_queryset(self):
        return (
            Payment.objects.filter(customer=self.request.user)
            .select_related("booking")
            .prefetch_related("orders__transactions")
        )


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    """
    POST /api/payments/webhook/ — Razorpay calls this directly, with
    no session, no cookie, and no JWT, so authentication is
    intentionally empty here (the *webhook signature* is the auth —
    see WebhookService.process_webhook) rather than DRF's normal
    authentication classes, and csrf_exempt is required for the same
    reason any server-to-server webhook endpoint needs it: there is no
    Django session/CSRF cookie in play for Razorpay's servers to echo
    back.

    Reads request.body (raw bytes) rather than request.data
    specifically because webhook signature verification is over the
    *exact bytes* Razorpay sent — re-serializing DRF's parsed JSON
    before hashing would silently break every signature (key
    ordering, whitespace) even for a completely legitimate webhook.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature", "")
        event_id = request.headers.get("X-Razorpay-Event-Id", "")
        raw_body = request.body.decode("utf-8")

        try:
            WebhookService.process_webhook(raw_body=raw_body, signature=signature, event_id=event_id)
        except DjangoValidationError as exc:
            # A 4xx here tells Razorpay this delivery failed and to
            # retry — correct for "signature verification failed" or
            # "missing event id", both of which are either an attack
            # or a misconfiguration, not something more retries fix on
            # their own, but returning 4xx (not 5xx) still avoids
            # Razorpay's automatic webhook-disable-after-24h-of-failures
            # behavior being triggered by something that will never
            # resolve itself.
            raise _django_validation_to_drf(exc)

        # Razorpay requires a 2xx within 5 seconds or it queues a
        # retry — this response carries no data because none is
        # needed for that contract.
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


# =====================================================================
# Admin payment foundation — read-only, matching admin.py's own "admin
# must NOT be able to edit historical financial transaction records
# directly". Full drill-down (individual PaymentOrder/PaymentTransaction/
# PaymentEvent/Refund/WebhookEvent rows) is already available via
# Django admin (apps/payments/admin.py, also fully read-only); this
# endpoint backs the frontend admin panel's own at-a-glance Payments
# list rather than duplicating that full detail view as custom React.
# =====================================================================


class AdminPaymentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminPaymentSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "amount", "captured_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Payment.objects.select_related("booking", "customer").prefetch_related("orders__transactions")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status__in=status_param.split(","))
        phase_param = self.request.query_params.get("phase")
        if phase_param:
            qs = qs.filter(phase=phase_param)
        return qs