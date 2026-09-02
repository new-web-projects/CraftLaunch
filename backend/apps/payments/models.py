"""
Part 6 — Razorpay payment foundation.

References apps.bookings (Booking) by FK, same one-directional
dependency rule the rest of the project already follows (catalog
doesn't know about bookings; bookings doesn't know about payments).
apps.bookings.services *does* import from apps.payments.services for
one thing — the advance/final-payment gate on starting work and
accepting delivery — but that's a local import inside those two
functions specifically to avoid any module-load-order coupling
between the two apps; nothing here imports anything from
apps.bookings.services.

Five entities, deliberately kept separate rather than folded into one
big "Payment" row:

  Payment            One logical row per (booking, phase) — "the
                      advance payment for this booking". Never
                      duplicated; retries reuse it.
  PaymentOrder        One row per Razorpay Order creation attempt.
                      A Payment can have several if the customer's
                      first attempt expires/fails/is cancelled and
                      they retry — each retry is a new Razorpay Order,
                      but still the same logical Payment.
  PaymentTransaction  One row per actual Razorpay payment_id that
                      lands against a PaymentOrder — the verified (or
                      failed) attempt itself.
  PaymentEvent        Append-only audit trail, the same role
                      BookingTimeline plays for bookings — every
                      order-created / verification-attempted /
                      verified / failed / webhook-received /
                      reconciliation-mismatch moment, permanent and
                      never user-editable.
  WebhookEvent        Raw idempotency ledger keyed on Razorpay's own
                      x-razorpay-event-id header (see money.py's
                      neighbour, services.py's WebhookService,
                      for why that header specifically — Razorpay's
                      documented, stable per-event identifier).

Plus Refund (foundation only — no refund-initiation endpoint in this
part, just the record and the webhook handling for it) and
ProjectPriceSnapshot (the frozen agreed price, so an admin changing a
Package's catalog price later can never move the ground under a
payment that's already in flight or completed).

No payment instrument data lives here at all — no card number, no
CVV, no UPI PIN, no bank credentials. Razorpay is the system of record
for all of that; this app only ever stores identifiers, amounts, and
status.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.bookings.models import Booking
from apps.core.models import TimeStampedModel, UUIDModel


class Payment(UUIDModel, TimeStampedModel):
    """
    The phase-level record — "the advance payment for booking X" or
    "the final payment for booking X". Exactly one per (booking,
    phase); a failed or abandoned checkout attempt doesn't create a
    new Payment, it creates a new PaymentOrder against this same one
    and this row's status moves back to ORDER_CREATED for the retry.
    """

    class Phase(models.TextChoices):
        ADVANCE_PAYMENT = "ADVANCE_PAYMENT", "Advance Payment"
        FINAL_PAYMENT = "FINAL_PAYMENT", "Final Payment"

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        ORDER_CREATED = "ORDER_CREATED", "Order Created"
        PENDING = "PENDING", "Pending"
        AUTHORIZED = "AUTHORIZED", "Authorized"
        CAPTURED = "CAPTURED", "Captured"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially Refunded"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"
        VERIFICATION_FAILED = "VERIFICATION_FAILED", "Verification Failed"

    TERMINAL_STATUSES = {Status.CAPTURED, Status.REFUNDED, Status.CANCELLED}

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="payments")
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
        limit_choices_to={"role": "CUSTOMER"},
        help_text="Denormalized from booking.customer at creation time for direct "
        "querying (a customer's full payment history shouldn't require joining "
        "through every booking) — booking.customer remains the source of truth.",
    )
    phase = models.CharField(max_length=20, choices=Phase.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Rupees, not paise — see money.py.")
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.CREATED, db_index=True)

    captured_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=50, blank=True, default="")
    failure_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Exactly one logical Payment per booking+phase — retries
            # reuse this row via a new PaymentOrder, never a second
            # Payment. This is the DB-level backstop behind
            # PaymentOrderService's own get-or-create check.
            models.UniqueConstraint(fields=["booking", "phase"], name="unique_payment_per_booking_phase"),
        ]
        indexes = [
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["booking", "phase"]),
        ]

    def __str__(self):
        return f"{self.get_phase_display()} — {self.booking_id} ({self.status})"

    @property
    def is_captured(self) -> bool:
        return self.status == self.Status.CAPTURED


class PaymentOrder(UUIDModel, TimeStampedModel):
    """
    One Razorpay Order per row. amount/currency are captured again
    here (not just read off the parent Payment) so that even if a
    Payment's amount were ever recalculated, this row stays an
    immutable record of exactly what was sent to Razorpay for this
    specific order.
    """

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        ATTEMPTED = "ATTEMPTED", "Attempted"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    ACTIVE_STATUSES = {Status.CREATED, Status.ATTEMPTED}

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="orders")
    razorpay_order_id = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paise = models.PositiveBigIntegerField(help_text="What was actually sent to Razorpay — see money.py.")
    currency = models.CharField(max_length=3, default="INR")
    receipt = models.CharField(max_length=40, unique=True, help_text="Razorpay's receipt field — max 40 chars.")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.CREATED, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["payment", "-created_at"])]

    def __str__(self):
        return self.razorpay_order_id


class PaymentTransaction(UUIDModel, TimeStampedModel):
    """
    One verified-or-failed Razorpay payment attempt against an Order.
    razorpay_signature is stored for audit purposes only — it's a
    computed HMAC over public IDs, not a secret, so storing it
    post-verification carries none of the risk storing a card number
    would.
    """

    class Status(models.TextChoices):
        AUTHORIZED = "AUTHORIZED", "Authorized"
        CAPTURED = "CAPTURED", "Captured"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially Refunded"

    payment_order = models.ForeignKey(PaymentOrder, on_delete=models.PROTECT, related_name="transactions")
    razorpay_payment_id = models.CharField(max_length=64, unique=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    method = models.CharField(
        max_length=20, blank=True, default="", help_text="card / upi / netbanking / wallet — from Razorpay, not entered."
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    # Deliberately narrow — populated by services.py from a fixed,
    # reviewed field allow-list on Razorpay's payment entity (method,
    # bank, wallet, card network/last4/type — never a full card
    # number, never CVV, never any raw instrument identifier), not by
    # dumping Razorpay's full API response into the database.
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["payment_order", "-created_at"])]

    def __str__(self):
        return self.razorpay_payment_id


class PaymentEvent(models.Model):
    """
    Append-only audit trail — BookingTimeline's counterpart for
    payments. `payment` is nullable because some events (a webhook
    that fails signature verification, or one that arrives for an
    order_id we don't recognize) don't reliably resolve to one of our
    Payment rows, and the event is exactly as worth recording either
    way.
    """

    class EventType(models.TextChoices):
        ORDER_CREATED = "ORDER_CREATED", "Payment order created"
        VERIFICATION_ATTEMPTED = "VERIFICATION_ATTEMPTED", "Payment verification attempted"
        VERIFIED = "VERIFIED", "Payment verified"
        VERIFICATION_FAILED = "VERIFICATION_FAILED", "Payment verification failed"
        CAPTURED = "CAPTURED", "Payment captured"
        FAILED = "FAILED", "Payment failed"
        WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED", "Webhook received"
        WEBHOOK_VERIFICATION_FAILED = "WEBHOOK_VERIFICATION_FAILED", "Webhook verification failed"
        REFUND_INITIATED = "REFUND_INITIATED", "Refund initiated"
        REFUND_PROCESSED = "REFUND_PROCESSED", "Refund processed"
        RECONCILIATION_MISMATCH = "RECONCILIATION_MISMATCH", "Reconciliation mismatch"
        RECONCILIATION_OK = "RECONCILIATION_OK", "Reconciliation confirmed"

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Null for system/webhook-triggered events.",
    )
    description = models.CharField(max_length=255)
    # Safe, structured context only (razorpay_order_id, razorpay_payment_id,
    # error codes, amounts) — never a secret, never a full webhook body.
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["payment", "-created_at"])]

    def __str__(self):
        return f"{self.get_event_type_display()} ({self.created_at:%Y-%m-%d %H:%M})"


class Refund(UUIDModel, TimeStampedModel):
    """
    Foundation only, per the spec — no refund-*initiation* endpoint
    exists in this part. This model exists so the refund.created /
    refund.processed webhook events (WebhookService) have somewhere
    durable to land, and so a future part implementing actual refund
    automation has the record shape already in place rather than
    retrofitting it.
    """

    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        PROCESSED = "PROCESSED", "Processed"
        FAILED = "FAILED", "Failed"

    payment_transaction = models.ForeignKey(PaymentTransaction, on_delete=models.PROTECT, related_name="refunds")
    razorpay_refund_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.INITIATED)
    reason = models.CharField(max_length=255, blank=True, default="")
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.razorpay_refund_id or self.id} — {self.status}"


class WebhookEvent(models.Model):
    """
    The idempotency ledger. razorpay_event_id is the value of the
    `x-razorpay-event-id` request header — Razorpay's own documented,
    stable-across-retries per-event identifier (NOT something parsed
    out of the JSON body, which webhook events don't reliably carry
    at top level). The unique constraint on it is what actually
    prevents double-processing when Razorpay retries a delivery, not
    just an in-memory check.
    """

    razorpay_event_id = models.CharField(max_length=64, unique=True)
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    signature_verified = models.BooleanField(default=False)
    processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_type", "-created_at"])]

    def __str__(self):
        return f"{self.event_type} ({self.razorpay_event_id})"


class ProjectPriceSnapshot(models.Model):
    """
    The agreed price, frozen the moment a booking becomes financially
    active (the first time any PaymentOrder is created for it — see
    PaymentCalculationService.get_or_create_snapshot). An admin
    changing the Package's catalog price afterward can never move this
    number; every advance/final calculation for this booking reads
    from here, never from booking.package.starting_price directly.
    """

    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="price_snapshot")
    agreed_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    snapshotted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking_id} — {self.currency} {self.agreed_price}"