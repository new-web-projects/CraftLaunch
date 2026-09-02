from rest_framework import serializers

from apps.accounts.serializers import PublicUserSummarySerializer

from .models import Payment, PaymentEvent, PaymentOrder, PaymentTransaction, Refund, WebhookEvent
from .services import RazorpayClientFactory


class PaymentOrderResponseSerializer(serializers.ModelSerializer):
    """
    What the frontend gets back after creating an order — deliberately
    narrow. razorpay_key_id is the one secret-adjacent value included,
    and it's the *public* Key ID Razorpay Checkout needs client-side;
    razorpay_key_secret and the webhook secret are never serialized
    anywhere in this app.
    """

    payment_id = serializers.UUIDField(source="payment.id", read_only=True)
    phase = serializers.CharField(source="payment.phase", read_only=True)
    razorpay_key_id = serializers.SerializerMethodField()

    class Meta:
        model = PaymentOrder
        fields = [
            "id", "payment_id", "phase", "razorpay_order_id", "amount", "amount_paise",
            "currency", "status", "razorpay_key_id", "created_at",
        ]
        read_only_fields = fields

    def get_razorpay_key_id(self, obj):
        return RazorpayClientFactory.get_config().razorpay_key_id


class PaymentVerifySerializer(serializers.Serializer):
    """Input shape for the verify endpoints — exactly the three values
    Razorpay Checkout hands back to the frontend on success, and
    nothing else. The frontend cannot send a status or an amount here;
    every one of those is looked up server-side."""

    razorpay_order_id = serializers.CharField(max_length=64)
    razorpay_payment_id = serializers.CharField(max_length=64)
    razorpay_signature = serializers.CharField(max_length=255)


class PaymentSerializer(serializers.ModelSerializer):
    phase_display = serializers.CharField(source="get_phase_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "phase", "phase_display", "amount", "currency", "status", "status_display",
            "created_at", "updated_at", "captured_at", "failure_reason",
        ]
        read_only_fields = fields


class PaymentHistoryItemSerializer(serializers.ModelSerializer):
    """Customer-facing history row. `transaction_reference` is the
    Razorpay payment ID of the latest successful transaction only —
    safe to show (it's what a customer would quote to support), never
    a signature or any raw gateway response."""

    phase_display = serializers.CharField(source="get_phase_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    website_name = serializers.CharField(source="booking.website_name", read_only=True)
    booking_id = serializers.UUIDField(source="booking.id", read_only=True)
    transaction_reference = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id", "booking_id", "website_name", "phase", "phase_display", "amount", "currency",
            "status", "status_display", "transaction_reference", "created_at", "captured_at",
        ]
        read_only_fields = fields

    def get_transaction_reference(self, payment):
        latest_order = payment.orders.order_by("-created_at").first()
        if not latest_order:
            return None
        txn = latest_order.transactions.filter(status=PaymentTransaction.Status.CAPTURED).order_by("-created_at").first()
        return txn.razorpay_payment_id if txn else None


class ProjectPaymentSummarySerializer(serializers.Serializer):
    """Mirrors the dict shape of
    PaymentCalculationService.get_project_summary() exactly — this
    serializer exists purely to give that dict a documented, typed API
    response shape; it performs no calculation of its own."""

    booking_id = serializers.UUIDField()
    has_snapshot = serializers.BooleanField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    advance_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    final_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    advance_payment_id = serializers.UUIDField(allow_null=True)
    advance_payment_status = serializers.CharField(allow_null=True)
    final_payment_id = serializers.UUIDField(allow_null=True)
    final_payment_status = serializers.CharField(allow_null=True)
    is_advance_captured = serializers.BooleanField()
    is_final_captured = serializers.BooleanField()


# ---- Admin-facing (read-only, per "admin must NOT be able to edit
# historical financial transaction records directly") ----


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ["id", "razorpay_payment_id", "status", "method", "verified_at", "captured_at", "created_at"]
        read_only_fields = fields


class PaymentOrderSerializer(serializers.ModelSerializer):
    transactions = PaymentTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentOrder
        fields = ["id", "razorpay_order_id", "amount", "currency", "receipt", "status", "created_at", "transactions"]
        read_only_fields = fields


class AdminPaymentSerializer(serializers.ModelSerializer):
    """Fuller shape for the admin panel — same model, more fields than
    the customer-facing PaymentSerializer, still nothing that isn't
    already safe (no signatures, no raw gateway payloads)."""

    phase_display = serializers.CharField(source="get_phase_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    customer = PublicUserSummarySerializer(read_only=True)
    website_name = serializers.CharField(source="booking.website_name", read_only=True)
    booking_id = serializers.UUIDField(source="booking.id", read_only=True)
    orders = PaymentOrderSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "booking_id", "website_name", "customer", "phase", "phase_display", "amount", "currency",
            "status", "status_display", "failure_code", "failure_reason",
            "created_at", "updated_at", "captured_at", "orders",
        ]
        read_only_fields = fields


class PaymentEventSerializer(serializers.ModelSerializer):
    actor = PublicUserSummarySerializer(read_only=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    payment_id = serializers.UUIDField(source="payment.id", read_only=True, allow_null=True)

    class Meta:
        model = PaymentEvent
        fields = ["id", "payment_id", "event_type", "event_type_display", "actor", "description", "metadata", "created_at"]
        read_only_fields = fields


class RefundSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Refund
        fields = ["id", "razorpay_refund_id", "amount", "status", "status_display", "reason", "created_at", "processed_at"]
        read_only_fields = fields


class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = [
            "id", "razorpay_event_id", "event_type", "signature_verified",
            "processed", "processed_at", "error_message", "created_at",
        ]
        read_only_fields = fields