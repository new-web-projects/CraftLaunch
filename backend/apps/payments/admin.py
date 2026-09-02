from django.contrib import admin

from .models import Payment, PaymentEvent, PaymentOrder, PaymentTransaction, ProjectPriceSnapshot, Refund, WebhookEvent


class PaymentOrderInline(admin.TabularInline):
    """Read-only — see PaymentAdmin's docstring for why nothing in
    this app is editable from Django admin."""

    model = PaymentOrder
    extra = 0
    fields = ("razorpay_order_id", "amount", "currency", "status", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PaymentEventInline(admin.TabularInline):
    model = PaymentEvent
    extra = 0
    fields = ("event_type", "description", "actor", "created_at")
    readonly_fields = fields
    can_delete = False
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Every field is read-only and every add/delete permission is
    disabled — per the spec's 'admin must NOT be able to edit
    historical financial transaction records directly'. This is a
    viewer onto the payment ledger, not an editor; any legitimate
    correction (a manual capture override, a reconciliation fix) goes
    through a dedicated service call with its own audit trail, not a
    raw Django admin field edit that would leave no record of why.
    """

    list_display = ("id", "booking", "customer", "phase", "amount", "currency", "status", "created_at", "captured_at")
    list_filter = ("phase", "status", "currency")
    search_fields = ("id", "booking__website_name", "customer__username", "customer__email")
    autocomplete_fields = ["booking", "customer"]
    readonly_fields = [f.name for f in Payment._meta.fields]
    inlines = [PaymentOrderInline, PaymentEventInline]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # Viewable (change form renders, all read-only), never savable.
        return True


class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    fields = ("razorpay_payment_id", "status", "method", "verified_at", "captured_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ("razorpay_order_id", "payment", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("razorpay_order_id", "receipt", "payment__id")
    readonly_fields = [f.name for f in PaymentOrder._meta.fields]
    inlines = [PaymentTransactionInline]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("razorpay_payment_id", "payment_order", "status", "method", "captured_at")
    list_filter = ("status", "method")
    search_fields = ("razorpay_payment_id", "payment_order__razorpay_order_id")
    readonly_fields = [f.name for f in PaymentTransaction._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    """The audit trail itself — see PaymentEvent's model docstring.
    Naturally has no add permission (nothing should ever hand-author
    an audit entry) on top of the usual no-edit rule."""

    list_display = ("event_type", "payment", "actor", "description", "created_at")
    list_filter = ("event_type",)
    search_fields = ("description", "payment__id")
    readonly_fields = [f.name for f in PaymentEvent._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("razorpay_refund_id", "payment_transaction", "amount", "status", "created_at", "processed_at")
    list_filter = ("status",)
    search_fields = ("razorpay_refund_id", "payment_transaction__razorpay_payment_id")
    readonly_fields = [f.name for f in Refund._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "razorpay_event_id", "signature_verified", "processed", "created_at")
    list_filter = ("event_type", "signature_verified", "processed")
    search_fields = ("razorpay_event_id", "event_type")
    readonly_fields = [f.name for f in WebhookEvent._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProjectPriceSnapshot)
class ProjectPriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("booking", "agreed_price", "currency", "snapshotted_at")
    search_fields = ("booking__website_name", "booking__id")
    readonly_fields = [f.name for f in ProjectPriceSnapshot._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False