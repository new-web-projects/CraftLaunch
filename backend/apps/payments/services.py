"""
Business logic for Razorpay payments. Every rupee amount here is a
Decimal; every conversion to/from paise goes through money.py; every
status change goes through _transition (this module's equivalent of
apps.bookings.services.BookingService.transition_status) so an
"arbitrary status change" — explicitly disallowed by the spec — simply
can't happen anywhere in this file.

Layout:
  RazorpayClientFactory    Builds an authenticated razorpay.Client
                            from apps.configuration's PaymentConfiguration.
                            The one place a Client gets constructed.
  PaymentEventService       Tiny helper — one line to append a
                            PaymentEvent, mirroring
                            apps.bookings.services.NotificationService.
  PaymentCalculationService The one source of truth for every money
                            number this app shows anyone.
  PaymentOrderService        Order creation: ownership, project-state,
                            phase, and duplicate-order checks, then
                            the actual Razorpay API call.
  PaymentVerificationService Server-side signature + Razorpay-API
                            cross-check verification of a checkout
                            result. Never trusts the frontend.
  WebhookService              Signature verification + idempotency +
                            event routing for the Razorpay webhook.
  ReconciliationService       Compares internal state against
                            Razorpay's own — logs mismatches, never
                            silently overwrites history.
"""

from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal

import razorpay
import razorpay.errors
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.configuration.services import get_payment_configuration

from . import lifecycle
from .models import (
    Payment,
    PaymentEvent,
    PaymentOrder,
    PaymentTransaction,
    ProjectPriceSnapshot,
    WebhookEvent,
)
from .money import round_money, split_advance_and_final, to_paise

logger = logging.getLogger(__name__)

# Fixed allow-list of Razorpay payment-entity fields safe to persist —
# never the full API response. None of these are payment instrument
# secrets: method/bank/wallet/vpa/card_id are identifiers Razorpay
# itself considers safe to return to a merchant server, not card
# numbers or PINs.
_SAFE_PAYMENT_FIELDS = ("method", "bank", "wallet", "vpa", "card_id", "email", "contact")


class RazorpayClientFactory:
    """The one place a razorpay.Client gets constructed, and the one
    place PaymentConfiguration's is_enabled flag actually gets
    enforced before any Razorpay API call is allowed to happen."""

    @staticmethod
    def get_config():
        return get_payment_configuration()

    @staticmethod
    def get_client() -> razorpay.Client:
        config = RazorpayClientFactory.get_config()
        if not config.is_enabled:
            raise ValidationError("Payments are not currently enabled on this platform.")
        if not config.razorpay_key_id or not config.razorpay_key_secret:
            raise ValidationError("The payment gateway has not been configured yet.")
        return razorpay.Client(auth=(config.razorpay_key_id, config.razorpay_key_secret))


class PaymentEventService:
    @staticmethod
    def log(*, payment=None, event_type: str, description: str, actor=None, metadata: dict | None = None) -> PaymentEvent:
        return PaymentEvent.objects.create(
            payment=payment, event_type=event_type, actor=actor, description=description, metadata=metadata or {}
        )


def _transition(payment: Payment, new_status: str) -> None:
    """Every Payment.status write in this module goes through here —
    see apps.bookings.lifecycle for why this pattern exists. An
    invalid edge raises rather than silently writing an unreviewed
    status; a webhook hitting this (out-of-order delivery, a status
    Razorpay already moved past) logs a RECONCILIATION_MISMATCH event
    instead of raising, since a webhook handler failing loudly just
    makes Razorpay retry the same "invalid" transition forever."""
    if not lifecycle.is_valid_transition(payment.status, new_status):
        raise ValidationError(lifecycle.describe_invalid_transition(payment.status, new_status))
    payment.status = new_status
    payment.save(update_fields=["status", "updated_at"])


class PaymentCalculationService:
    """The one source of truth for every money number this app shows
    anyone — the spec is explicit that duplicating this math in a
    view, a serializer, or a React component is not allowed."""

    ADVANCE_PERCENT = Decimal("50")

    @staticmethod
    @transaction.atomic
    def get_or_create_snapshot(booking) -> ProjectPriceSnapshot:
        """'When a booking becomes financially active, create a price
        snapshot' — this is that trigger point, called from
        PaymentOrderService.create_order the first time any order is
        requested for a booking. get_or_create-shaped (via a locked
        get-then-create, since ProjectPriceSnapshot doesn't need its
        own get_or_create race protection beyond the OneToOne
        constraint already guaranteeing at most one row)."""
        try:
            return booking.price_snapshot
        except ProjectPriceSnapshot.DoesNotExist:
            currency = RazorpayClientFactory.get_config().default_currency or "INR"
            return ProjectPriceSnapshot.objects.create(
                booking=booking, agreed_price=booking.package.starting_price, currency=currency
            )

    @staticmethod
    def get_project_summary(booking) -> dict:
        """Everything a frontend needs to render a payment summary —
        computed fresh on every call, never cached, and the frontend
        never recomputes any of these numbers itself (see the Part 6
        spec's explicit 'do not calculate the authoritative amount on
        the frontend')."""
        try:
            snapshot = booking.price_snapshot
        except ProjectPriceSnapshot.DoesNotExist:
            snapshot = None

        total = snapshot.agreed_price if snapshot else booking.package.starting_price
        currency = snapshot.currency if snapshot else "INR"
        advance_amount, final_amount = split_advance_and_final(total, advance_percent=PaymentCalculationService.ADVANCE_PERCENT)

        advance_payment = Payment.objects.filter(booking=booking, phase=Payment.Phase.ADVANCE_PAYMENT).first()
        final_payment = Payment.objects.filter(booking=booking, phase=Payment.Phase.FINAL_PAYMENT).first()

        amount_paid = Decimal("0.00")
        if advance_payment and advance_payment.status == Payment.Status.CAPTURED:
            amount_paid += advance_payment.amount
        if final_payment and final_payment.status == Payment.Status.CAPTURED:
            amount_paid += final_payment.amount
        amount_paid = round_money(amount_paid)

        return {
            "booking_id": booking.id,
            "has_snapshot": snapshot is not None,
            "total_amount": total,
            "currency": currency,
            "advance_amount": advance_amount,
            "final_amount": final_amount,
            "amount_paid": amount_paid,
            "amount_due": round_money(total - amount_paid),
            "advance_payment_id": advance_payment.id if advance_payment else None,
            "advance_payment_status": advance_payment.status if advance_payment else None,
            "final_payment_id": final_payment.id if final_payment else None,
            "final_payment_status": final_payment.status if final_payment else None,
            "is_advance_captured": bool(advance_payment and advance_payment.status == Payment.Status.CAPTURED),
            "is_final_captured": bool(final_payment and final_payment.status == Payment.Status.CAPTURED),
        }

    @staticmethod
    def is_advance_captured(booking) -> bool:
        """The one function apps.bookings.services calls (via a local
        import — see its ProjectLifecycleService.start_project) to
        decide whether work is allowed to begin. Defining "captured"
        once, here, is what makes that gate and this module's own
        summary agree by construction rather than by convention."""
        return Payment.objects.filter(
            booking=booking, phase=Payment.Phase.ADVANCE_PAYMENT, status=Payment.Status.CAPTURED
        ).exists()

    @staticmethod
    def is_final_captured(booking) -> bool:
        return Payment.objects.filter(
            booking=booking, phase=Payment.Phase.FINAL_PAYMENT, status=Payment.Status.CAPTURED
        ).exists()


class PaymentOrderService:
    """Order creation — the one place that talks to Razorpay's Orders
    API. Every check the spec lists (auth, ownership, phase, project
    state, amount, currency, duplicate-order prevention) happens here,
    in this order, before the API call — not scattered across the
    view and the serializer."""

    ADVANCE_ELIGIBLE_STATUSES = {
        "accepted", "in_progress", "waiting_for_customer", "revision_requested", "ready_for_delivery",
    }
    FINAL_ELIGIBLE_STATUSES = {"ready_for_delivery", "delivered"}

    @staticmethod
    def create_order(booking, *, phase: str, customer) -> PaymentOrder:
        if booking.customer_id != customer.id:
            raise ValidationError("You do not have access to this booking.")

        status_code = booking.status.code
        if phase == Payment.Phase.ADVANCE_PAYMENT:
            if status_code not in PaymentOrderService.ADVANCE_ELIGIBLE_STATUSES:
                raise ValidationError("This project is not yet eligible for the advance payment.")
        elif phase == Payment.Phase.FINAL_PAYMENT:
            if status_code not in PaymentOrderService.FINAL_ELIGIBLE_STATUSES:
                raise ValidationError("This project is not yet eligible for the final payment.")
            if not PaymentCalculationService.is_advance_captured(booking):
                raise ValidationError("The advance payment must be completed before the final payment.")
        else:
            raise ValidationError("Unknown payment phase.")

        snapshot = PaymentCalculationService.get_or_create_snapshot(booking)
        advance_amount, final_amount = split_advance_and_final(
            snapshot.agreed_price, advance_percent=PaymentCalculationService.ADVANCE_PERCENT
        )
        amount = advance_amount if phase == Payment.Phase.ADVANCE_PAYMENT else final_amount

        # Lock held only for this short, no-network section — reserve/
        # check the Payment row's state, then release before the slow
        # Razorpay API call below. Holding a DB row lock for the
        # duration of an external HTTP call would serialize every
        # concurrent request through that one call's latency for no
        # benefit; the lock only needs to protect the "is a duplicate
        # order about to be created" decision itself, the same
        # decision accept_project's lock protects in
        # apps.bookings.services.
        with transaction.atomic():
            payment, created = Payment.objects.select_for_update().get_or_create(
                booking=booking,
                phase=phase,
                defaults={
                    "customer": customer, "amount": amount, "currency": snapshot.currency, "status": Payment.Status.CREATED,
                },
            )

            if payment.status == Payment.Status.CAPTURED:
                raise ValidationError(f"The {payment.get_phase_display()} has already been completed.")

            if not created and payment.status not in lifecycle.RETRYABLE_STATUSES:
                # An order is already actively in flight (ORDER_CREATED /
                # PENDING / AUTHORIZED) — return that one rather than
                # creating a duplicate Razorpay order, per the spec's
                # "prevent duplicate active orders".
                active_order = payment.orders.filter(status__in=PaymentOrder.ACTIVE_STATUSES).order_by("-created_at").first()
                if active_order:
                    return active_order
            payment_id = payment.id

        client = RazorpayClientFactory.get_client()
        amount_paise = to_paise(amount)
        # uuid4, not a timestamp — a timestamp only has second-level
        # resolution, so two retries within the same second (a
        # perfectly normal "duplicate click" scenario, not just a
        # test artifact) would collide on this field's unique
        # constraint. "adv"/"fin" + 28 hex chars stays comfortably
        # under Razorpay's 40-character receipt limit.
        receipt_prefix = "adv" if phase == Payment.Phase.ADVANCE_PAYMENT else "fin"
        receipt = f"{receipt_prefix}_{uuid.uuid4().hex[:28]}"

        try:
            razorpay_order = client.order.create(
                data={
                    "amount": amount_paise,
                    "currency": payment.currency,
                    "receipt": receipt,
                    "notes": {
                        "booking_id": str(booking.id),
                        "payment_id": str(payment_id),
                        "phase": phase,
                    },
                }
            )
        except (razorpay.errors.BadRequestError, razorpay.errors.ServerError, razorpay.errors.GatewayError) as exc:
            # Deliberately NOT inside the atomic block above (it has
            # already exited by this point) — this log entry must
            # survive even though create_order is about to raise. A
            # single PaymentEventService.log() call is one INSERT,
            # already atomic on its own; no explicit wrapper needed.
            PaymentEventService.log(
                payment=payment, event_type=PaymentEvent.EventType.FAILED, actor=customer,
                description=f"Razorpay order creation failed: {exc}",
            )
            raise ValidationError("Could not create a payment order right now. Please try again.")

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=payment_id)
            order = PaymentOrder.objects.create(
                payment=payment,
                razorpay_order_id=razorpay_order["id"],
                amount=amount,
                amount_paise=amount_paise,
                currency=payment.currency,
                receipt=receipt,
                status=PaymentOrder.Status.CREATED,
            )
            if payment.status != Payment.Status.ORDER_CREATED:
                _transition(payment, Payment.Status.ORDER_CREATED)
            PaymentEventService.log(
                payment=payment, event_type=PaymentEvent.EventType.ORDER_CREATED, actor=customer,
                description=f"Razorpay order created for {payment.get_phase_display()}.",
                metadata={"razorpay_order_id": order.razorpay_order_id, "amount_paise": amount_paise},
            )
        return order


class PaymentVerificationService:
    """Server-side verification of a checkout result. This is the
    only path by which a Payment may ever reach CAPTURED from a
    frontend-initiated request — see the module docstring and the
    spec's 'never mark a payment successful merely because the
    frontend said so'."""

    @staticmethod
    def verify_payment(
        payment_order_id, *, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str, customer
    ) -> Payment:
        # No select_for_update()/outer atomic here — unlike
        # accept_project's race (two developers, one booking, a real
        # correctness invariant to protect), a duplicate verify call
        # for the same razorpay_payment_id is already safe without a
        # lock: PaymentTransaction.update_or_create is keyed on that
        # column's own unique constraint, so two near-simultaneous
        # calls just update the same row twice — idempotent, not a
        # race that needs serializing.
        try:
            payment_order = PaymentOrder.objects.select_related("payment", "payment__booking").get(pk=payment_order_id)
        except PaymentOrder.DoesNotExist:
            raise ValidationError("Payment order not found.")

        payment = payment_order.payment

        if payment.customer_id != customer.id:
            raise ValidationError("You do not have access to this payment.")

        PaymentEventService.log(
            payment=payment, event_type=PaymentEvent.EventType.VERIFICATION_ATTEMPTED, actor=customer,
            description="Payment verification attempted.",
            metadata={"razorpay_order_id": razorpay_order_id, "razorpay_payment_id": razorpay_payment_id},
        )

        def fail(reason: str) -> None:
            # Its own small transaction, deliberately not nested
            # inside anything this function later raises out of —
            # see the module-level note on _transition. A
            # verification failure must be recorded, and this is what
            # makes that record survive the ValidationError raised
            # right after every call site below.
            with transaction.atomic():
                if lifecycle.is_valid_transition(payment.status, Payment.Status.VERIFICATION_FAILED):
                    payment.status = Payment.Status.VERIFICATION_FAILED
                    payment.failure_reason = reason
                    payment.save(update_fields=["status", "failure_reason", "updated_at"])
                PaymentEventService.log(
                    payment=payment, event_type=PaymentEvent.EventType.VERIFICATION_FAILED, actor=customer, description=reason
                )

        # Wrong-order check: the order_id the client is asserting must
        # be the one we actually created for this PaymentOrder row —
        # not just "some valid Razorpay order".
        if razorpay_order_id != payment_order.razorpay_order_id:
            fail("Razorpay order ID does not match the expected order.")
            raise ValidationError("This payment does not match the expected order.")

        client = RazorpayClientFactory.get_client()

        # Signature verification — proves the (order_id, payment_id)
        # pairing is authentic and unmodified.
        try:
            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                }
            )
        except razorpay.errors.SignatureVerificationError:
            fail("Signature verification failed.")
            raise ValidationError("Payment verification failed. If you were charged, contact support.")

        # A valid signature alone only proves that pairing is
        # authentic — it says nothing about the amount actually
        # captured. Fetch the payment from Razorpay's own API and
        # cross-check everything that matters before trusting it.
        try:
            razorpay_payment = client.payment.fetch(razorpay_payment_id)
        except (razorpay.errors.BadRequestError, razorpay.errors.ServerError, razorpay.errors.GatewayError):
            fail("Could not fetch payment details from Razorpay for cross-verification.")
            raise ValidationError("Could not confirm this payment with the payment gateway. Please try again shortly.")

        if razorpay_payment.get("order_id") != razorpay_order_id:
            fail("Fetched payment's order_id does not match.")
            raise ValidationError("This payment does not match the expected order.")

        expected_paise = to_paise(payment_order.amount)
        if razorpay_payment.get("amount") != expected_paise:
            fail(f"Amount mismatch: expected {expected_paise} paise, Razorpay reports {razorpay_payment.get('amount')}.")
            raise ValidationError("The payment amount does not match what was expected.")

        if razorpay_payment.get("currency") != payment_order.currency:
            fail(f"Currency mismatch: expected {payment_order.currency}, Razorpay reports {razorpay_payment.get('currency')}.")
            raise ValidationError("The payment currency does not match what was expected.")

        razorpay_status = razorpay_payment.get("status")
        if razorpay_status not in ("authorized", "captured"):
            fail(f"Unexpected Razorpay payment status: {razorpay_status!r}.")
            raise ValidationError("This payment has not completed successfully.")

        # Every check passed — this sequence genuinely is
        # all-or-nothing, so (unlike the checks above) it does belong
        # in one atomic block.
        is_captured = razorpay_status == "captured"
        safe_fields = {k: razorpay_payment.get(k) for k in _SAFE_PAYMENT_FIELDS}

        with transaction.atomic():
            PaymentTransaction.objects.update_or_create(
                razorpay_payment_id=razorpay_payment_id,
                defaults={
                    "payment_order": payment_order,
                    "razorpay_signature": razorpay_signature,
                    "status": PaymentTransaction.Status.CAPTURED if is_captured else PaymentTransaction.Status.AUTHORIZED,
                    "method": safe_fields.get("method") or "",
                    "verified_at": timezone.now(),
                    "captured_at": timezone.now() if is_captured else None,
                    "raw_response": safe_fields,
                },
            )

            payment_order.status = PaymentOrder.Status.PAID if is_captured else PaymentOrder.Status.ATTEMPTED
            payment_order.save(update_fields=["status", "updated_at"])

            new_status = Payment.Status.CAPTURED if is_captured else Payment.Status.AUTHORIZED
            if payment.status != new_status:
                _transition(payment, new_status)
            if is_captured:
                payment.captured_at = timezone.now()
                payment.save(update_fields=["captured_at"])

            PaymentEventService.log(
                payment=payment,
                event_type=PaymentEvent.EventType.VERIFIED if is_captured else PaymentEvent.EventType.VERIFICATION_ATTEMPTED,
                actor=customer,
                description=f"Payment verified — Razorpay status {razorpay_status}.",
                metadata={"razorpay_payment_id": razorpay_payment_id},
            )
        return payment


class WebhookService:
    """
    Signature verification, idempotency, and event routing for
    POST /api/payments/webhook/. Order of operations matters:
    idempotency short-circuit first (cheapest check, avoids redundant
    HMAC work on a known-processed retry), then signature verification
    (never trust a payload before its signature is confirmed), then —
    only once both pass — parsing and acting on the body.
    """

    HANDLED_PAYMENT_EVENTS = {"payment.authorized", "payment.captured", "payment.failed"}
    HANDLED_REFUND_EVENTS = {"refund.created", "refund.processed"}

    @staticmethod
    def process_webhook(*, raw_body: str, signature: str, event_id: str) -> WebhookEvent:
        # No outer @transaction.atomic here — same reasoning as
        # verify_payment above. Every write below is either a single
        # statement (already atomic on its own) or, where several
        # writes genuinely need to succeed or fail together (see
        # _handle_payment_event/_handle_refund_event), wrapped in its
        # own targeted `with transaction.atomic():` block that isn't
        # nested inside anything this function later raises out of.
        # The bug this avoids: a blanket outer atomic would silently
        # roll back the WebhookEvent row itself the moment any
        # downstream check raises — exactly the row the spec requires
        # to survive ("store webhook event... support idempotency")
        # even when (especially when) processing fails.
        if not event_id:
            raise ValidationError("Missing x-razorpay-event-id header.")

        existing = WebhookEvent.objects.filter(razorpay_event_id=event_id).first()
        if existing and existing.processed:
            # Razorpay's at-least-once delivery means retries are
            # expected and normal, not an error condition — a
            # already-processed duplicate is a silent no-op, not a
            # 4xx (a 4xx would make Razorpay keep retrying forever).
            return existing

        config = RazorpayClientFactory.get_config()
        if not config.razorpay_webhook_secret:
            raise ValidationError("Webhook secret is not configured.")

        signature_verified = False
        try:
            razorpay.Utility(razorpay.Client(auth=("x", "x"))).verify_webhook_signature(
                raw_body, signature, config.razorpay_webhook_secret
            )
            signature_verified = True
        except razorpay.errors.SignatureVerificationError:
            signature_verified = False

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, TypeError):
            payload = {}
        event_type = payload.get("event", "unknown")

        webhook_event, _ = WebhookEvent.objects.update_or_create(
            razorpay_event_id=event_id,
            defaults={"event_type": event_type, "payload": payload, "signature_verified": signature_verified},
        )

        if not signature_verified:
            webhook_event.error_message = "Webhook signature verification failed."
            webhook_event.save(update_fields=["error_message"])
            PaymentEventService.log(
                event_type=PaymentEvent.EventType.WEBHOOK_VERIFICATION_FAILED,
                description=f"Webhook signature verification failed for event {event_id} ({event_type}).",
            )
            raise ValidationError("Webhook signature verification failed.")

        try:
            WebhookService._route_event(webhook_event, payload, event_type)
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any handler failure must still
            # leave the WebhookEvent row recording the attempt, so a bug in one
            # handler doesn't look identical to "never received" on retry.
            webhook_event.error_message = str(exc)[:500]
            webhook_event.save(update_fields=["error_message"])
            raise

        webhook_event.processed = True
        webhook_event.processed_at = timezone.now()
        webhook_event.save(update_fields=["processed", "processed_at"])
        return webhook_event

    @staticmethod
    def _route_event(webhook_event: WebhookEvent, payload: dict, event_type: str) -> None:
        if event_type in WebhookService.HANDLED_PAYMENT_EVENTS:
            WebhookService._handle_payment_event(payload, event_type, webhook_event.razorpay_event_id)
        elif event_type in WebhookService.HANDLED_REFUND_EVENTS:
            WebhookService._handle_refund_event(payload, event_type)
        elif event_type == "order.paid":
            # Informational alongside payment.captured for the same
            # capture — payment.captured (handled above) is the
            # signal this app acts on, so there's nothing further to
            # do here beyond the WebhookEvent row already recording
            # receipt of it.
            pass
        else:
            PaymentEventService.log(
                event_type=PaymentEvent.EventType.WEBHOOK_RECEIVED, description=f"Received unhandled webhook event type: {event_type}."
            )

    @staticmethod
    def _handle_payment_event(payload: dict, event_type: str, razorpay_event_id: str) -> None:
        # Wrapped as one unit — select_for_update() below requires an
        # active transaction (Django raises otherwise), and everything
        # in this function is "the effects of processing one webhook
        # event," which genuinely belongs together: either they all
        # land, or (or a real, unexpected DB error) none do, and
        # process_webhook's caller records that failure via the
        # WebhookEvent row's error_message rather than silently
        # losing track of it.
        with transaction.atomic():
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            razorpay_payment_id = payment_entity.get("id")
            razorpay_order_id = payment_entity.get("order_id")

            if not razorpay_order_id:
                PaymentEventService.log(
                    event_type=PaymentEvent.EventType.WEBHOOK_RECEIVED,
                    description=f"Webhook {event_type} had no order_id; ignored.",
                    metadata={"razorpay_payment_id": razorpay_payment_id, "razorpay_event_id": razorpay_event_id},
                )
                return

            payment_order = (
                PaymentOrder.objects.select_for_update()
                .select_related("payment")
                .filter(razorpay_order_id=razorpay_order_id)
                .first()
            )
            if not payment_order:
                PaymentEventService.log(
                    event_type=PaymentEvent.EventType.WEBHOOK_RECEIVED,
                    description=f"Webhook {event_type} referenced unknown order {razorpay_order_id}.",
                    metadata={"razorpay_order_id": razorpay_order_id, "razorpay_event_id": razorpay_event_id},
                )
                return

            payment = payment_order.payment
            PaymentEventService.log(
                payment=payment, event_type=PaymentEvent.EventType.WEBHOOK_RECEIVED,
                description=f"Webhook received: {event_type}.",
                metadata={"razorpay_payment_id": razorpay_payment_id, "razorpay_event_id": razorpay_event_id},
            )

            if payment.status == Payment.Status.CAPTURED:
                # Already captured (most likely via the synchronous verify
                # endpoint, with this webhook arriving moments later as
                # Razorpay's own confirmation) — the payment event is
                # still logged above, but there's no state left to change,
                # and payment.failed arriving after a genuine capture is
                # exactly the late/out-of-order delivery Razorpay's own
                # docs warn about, not a reason to un-capture anything.
                return

            if event_type == "payment.failed":
                if lifecycle.is_valid_transition(payment.status, Payment.Status.FAILED):
                    payment.status = Payment.Status.FAILED
                    payment.failure_code = payment_entity.get("error_code", "") or ""
                    payment.failure_reason = payment_entity.get("error_description", "") or ""
                    payment.save(update_fields=["status", "failure_code", "failure_reason", "updated_at"])
                    PaymentEventService.log(
                        payment=payment, event_type=PaymentEvent.EventType.FAILED,
                        description=payment.failure_reason or "Payment failed.",
                    )
                return

            expected_paise = to_paise(payment_order.amount)
            if payment_entity.get("amount") != expected_paise:
                PaymentEventService.log(
                    payment=payment, event_type=PaymentEvent.EventType.RECONCILIATION_MISMATCH,
                    description=f"Webhook amount {payment_entity.get('amount')} != expected {expected_paise}.",
                    metadata={"razorpay_payment_id": razorpay_payment_id},
                )
                return

            is_captured = event_type == "payment.captured"
            safe_fields = {k: payment_entity.get(k) for k in _SAFE_PAYMENT_FIELDS}
            PaymentTransaction.objects.update_or_create(
                razorpay_payment_id=razorpay_payment_id,
                defaults={
                    "payment_order": payment_order,
                    "status": PaymentTransaction.Status.CAPTURED if is_captured else PaymentTransaction.Status.AUTHORIZED,
                    "method": safe_fields.get("method") or "",
                    "verified_at": timezone.now(),
                    "captured_at": timezone.now() if is_captured else None,
                    "raw_response": safe_fields,
                },
            )

            new_status = Payment.Status.CAPTURED if is_captured else Payment.Status.AUTHORIZED
            if lifecycle.is_valid_transition(payment.status, new_status):
                payment.status = new_status
                if is_captured:
                    payment.captured_at = timezone.now()
                    payment_order.status = PaymentOrder.Status.PAID
                    payment_order.save(update_fields=["status"])
                payment.save(update_fields=["status", "captured_at", "updated_at"])
                PaymentEventService.log(
                    payment=payment,
                    event_type=PaymentEvent.EventType.CAPTURED if is_captured else PaymentEvent.EventType.VERIFIED,
                    description=f"Payment {new_status.lower()} via webhook.",
                    metadata={"razorpay_payment_id": razorpay_payment_id},
                )
            else:
                PaymentEventService.log(
                    payment=payment, event_type=PaymentEvent.EventType.RECONCILIATION_MISMATCH,
                    description=f"Webhook {event_type} attempted invalid transition {payment.status} -> {new_status}; ignored.",
                )

    @staticmethod
    def _handle_refund_event(payload: dict, event_type: str) -> None:
        from .models import Refund  # local import: Refund is only ever touched from webhook handling

        refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
        razorpay_payment_id = refund_entity.get("payment_id")
        razorpay_refund_id = refund_entity.get("id")

        transaction_row = PaymentTransaction.objects.filter(razorpay_payment_id=razorpay_payment_id).first()
        if not transaction_row:
            PaymentEventService.log(
                event_type=PaymentEvent.EventType.WEBHOOK_RECEIVED,
                description=f"Refund webhook {event_type} for unknown payment {razorpay_payment_id}.",
                metadata={"razorpay_refund_id": razorpay_refund_id},
            )
            return

        # The Refund row, the audit event, and (for a processed
        # refund) the Payment status move all describe one outcome —
        # wrapped together so a mid-sequence failure can't leave a
        # Refund row recorded as PROCESSED while Payment.status still
        # says CAPTURED.
        with transaction.atomic():
            amount = round_money(Decimal(refund_entity.get("amount", 0)) / 100)
            status = Refund.Status.PROCESSED if event_type == "refund.processed" else Refund.Status.INITIATED
            Refund.objects.update_or_create(
                razorpay_refund_id=razorpay_refund_id,
                defaults={
                    "payment_transaction": transaction_row,
                    "amount": amount,
                    "status": status,
                    "processed_at": timezone.now() if status == Refund.Status.PROCESSED else None,
                },
            )

            payment = transaction_row.payment_order.payment
            event_type_enum = (
                PaymentEvent.EventType.REFUND_PROCESSED if status == Refund.Status.PROCESSED else PaymentEvent.EventType.REFUND_INITIATED
            )
            PaymentEventService.log(
                payment=payment, event_type=event_type_enum, description=f"Refund {status.lower()}: {razorpay_refund_id}.",
                metadata={"razorpay_refund_id": razorpay_refund_id, "amount": str(amount)},
            )

            # Full-vs-partial isn't in the webhook payload as a flag —
            # it's determined by comparing the refunded amount to the
            # original capture. Foundation-only, per the spec (no refund
            # *automation* in this part): this records the outcome, it
            # doesn't decide whether to issue one.
            if status == Refund.Status.PROCESSED and payment.status != Payment.Status.REFUNDED:
                full_refund = amount >= payment.amount
                target = Payment.Status.REFUNDED if full_refund else Payment.Status.PARTIALLY_REFUNDED
                if lifecycle.is_valid_transition(payment.status, target):
                    payment.status = target
                    payment.save(update_fields=["status", "updated_at"])


class ReconciliationService:
    """Compares this app's internal Payment state against Razorpay's
    own Order state. Never auto-corrects a mismatch — every mismatch
    becomes a PaymentEvent for manual review, per the spec's 'do not
    silently overwrite history'."""

    @staticmethod
    def reconcile(payment: Payment) -> dict:
        latest_order = payment.orders.order_by("-created_at").first()
        if not latest_order:
            return {"status": "no_order", "match": None}

        client = RazorpayClientFactory.get_client()
        try:
            razorpay_order = client.order.fetch(latest_order.razorpay_order_id)
        except (razorpay.errors.BadRequestError, razorpay.errors.ServerError, razorpay.errors.GatewayError) as exc:
            PaymentEventService.log(
                payment=payment, event_type=PaymentEvent.EventType.RECONCILIATION_MISMATCH,
                description=f"Could not fetch order from Razorpay for reconciliation: {exc}",
            )
            return {"status": "fetch_failed", "match": False}

        razorpay_order_status = razorpay_order.get("status")  # created / attempted / paid
        internal_paid = payment.status == Payment.Status.CAPTURED
        razorpay_paid = razorpay_order_status == "paid"

        if internal_paid == razorpay_paid:
            PaymentEventService.log(
                payment=payment, event_type=PaymentEvent.EventType.RECONCILIATION_OK,
                description="Internal and Razorpay payment state agree.",
            )
            return {"status": "match", "match": True, "razorpay_order_status": razorpay_order_status}

        PaymentEventService.log(
            payment=payment, event_type=PaymentEvent.EventType.RECONCILIATION_MISMATCH,
            description=(
                f"Internal status {payment.status} (paid={internal_paid}) disagrees with "
                f"Razorpay order status {razorpay_order_status} (paid={razorpay_paid})."
            ),
            metadata={"razorpay_order_status": razorpay_order_status, "internal_status": payment.status},
        )
        return {"status": "mismatch", "match": False, "razorpay_order_status": razorpay_order_status}