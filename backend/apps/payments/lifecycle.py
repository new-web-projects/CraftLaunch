"""
The payment state machine. Same role and same shape as
apps.bookings.lifecycle — a pure, side-effect-free adjacency graph
that services.py checks every transition against, so "arbitrary status
changes" (explicitly disallowed by the spec) simply can't happen: any
edge not listed here is rejected before a single field gets written.

Kept as its own module for the same reason bookings/lifecycle.py is —
so the graph itself is unit-testable without spinning up a Payment,
and so PaymentVerificationService/WebhookService/services.py don't
each carry their own copy of "which moves are legal."
"""

from __future__ import annotations

# Every valid edge. A status with no key here has no outgoing edges —
# REFUNDED is the only fully terminal one; PARTIALLY_REFUNDED can
# still move to a full REFUNDED later.
TRANSITIONS: dict[str, set[str]] = {
    "CREATED": {"ORDER_CREATED", "CANCELLED"},
    "ORDER_CREATED": {"PENDING", "AUTHORIZED", "CAPTURED", "FAILED", "CANCELLED", "EXPIRED", "VERIFICATION_FAILED"},
    "PENDING": {"AUTHORIZED", "CAPTURED", "FAILED", "CANCELLED", "EXPIRED", "VERIFICATION_FAILED"},
    "AUTHORIZED": {"CAPTURED", "FAILED", "REFUNDED"},
    "CAPTURED": {"REFUNDED", "PARTIALLY_REFUNDED"},
    # Every non-terminal failure-ish state can retry — a new
    # PaymentOrder gets created against the same Payment row, which is
    # what actually drives this edge (see PaymentOrderService).
    "FAILED": {"ORDER_CREATED"},
    "VERIFICATION_FAILED": {"ORDER_CREATED"},
    "CANCELLED": {"ORDER_CREATED"},
    "EXPIRED": {"ORDER_CREATED"},
    "PARTIALLY_REFUNDED": {"REFUNDED"},
}

TERMINAL_STATUSES = {"REFUNDED"}

# Statuses from which creating a fresh PaymentOrder (a retry) is
# allowed. Anything actively in flight (ORDER_CREATED, PENDING,
# AUTHORIZED) must resolve or be explicitly cancelled first — this is
# the rule behind "prevent duplicate active orders".
RETRYABLE_STATUSES = {"CREATED", "FAILED", "VERIFICATION_FAILED", "CANCELLED", "EXPIRED"}


def is_valid_transition(from_status: str, to_status: str) -> bool:
    return to_status in TRANSITIONS.get(from_status, set())


def describe_invalid_transition(from_status: str, to_status: str) -> str:
    if from_status in TERMINAL_STATUSES:
        return f"Payment status {from_status!r} is final and cannot be changed further."
    return f"Cannot move a payment from {from_status!r} to {to_status!r} directly."