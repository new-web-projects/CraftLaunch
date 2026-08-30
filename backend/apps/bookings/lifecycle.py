"""
Part 5 — the project lifecycle state machine.

Kept separate from services.py on purpose: this module is pure rules
(what transitions exist, who may trigger them) with no side effects
and no database writes, so the transition graph itself can be unit
tested and reasoned about without spinning up a booking. services.py
imports from here and does the actual DB work.

ProjectStatus rows are still the DB-backed catalog they were in Part 3
(apps/bookings/models.py) — this module doesn't replace that, it adds
the validation layer Part 3 didn't need yet: a lookup of which
`from_code -> to_code` edges are legal, and which role(s) may cross
each one. `transition_status()` in services.py was previously willing
to move a booking to *any* known status code with no adjacency check
at all; that gap is exactly what this module closes.
"""

from __future__ import annotations

from apps.accounts.models import Role

# Every valid edge in the state machine. A code that doesn't appear as
# a key has no outgoing transitions (the three terminal statuses:
# completed, cancelled, rejected).
TRANSITIONS: dict[str, set[str]] = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"awaiting_developer", "cancelled"},
    "awaiting_developer": {"accepted", "rejected", "cancelled"},
    "accepted": {"in_progress", "cancelled"},
    "in_progress": {"waiting_for_customer", "cancelled"},
    "waiting_for_customer": {"revision_requested", "ready_for_delivery", "delivered", "cancelled"},
    "revision_requested": {"in_progress", "cancelled"},
    "ready_for_delivery": {"delivered", "cancelled"},
    "delivered": {"completed", "revision_requested"},
}

# Which role(s) may trigger each edge. Not every edge needs an entry
# here — a few (submitted -> awaiting_developer) happen automatically
# as part of another action rather than being their own user-facing
# endpoint, so there's nothing to gate. ADMIN can always additionally
# perform any edge that appears here (checked separately in
# can_transition below) — it's not repeated on every line.
TRANSITION_ACTORS: dict[tuple[str, str], set[str]] = {
    ("draft", "submitted"): {Role.CUSTOMER},
    ("draft", "cancelled"): {Role.CUSTOMER},
    ("submitted", "cancelled"): {Role.CUSTOMER},
    ("awaiting_developer", "accepted"): {Role.DEVELOPER},
    ("awaiting_developer", "rejected"): {Role.DEVELOPER},
    ("awaiting_developer", "cancelled"): {Role.CUSTOMER},
    ("accepted", "in_progress"): {Role.DEVELOPER},
    ("accepted", "cancelled"): {Role.CUSTOMER},
    ("in_progress", "waiting_for_customer"): {Role.DEVELOPER},
    ("in_progress", "cancelled"): {Role.CUSTOMER},
    ("waiting_for_customer", "revision_requested"): {Role.CUSTOMER},
    ("waiting_for_customer", "ready_for_delivery"): {Role.DEVELOPER},
    ("waiting_for_customer", "delivered"): {Role.DEVELOPER},
    ("waiting_for_customer", "cancelled"): {Role.CUSTOMER},
    ("revision_requested", "in_progress"): {Role.DEVELOPER},
    ("revision_requested", "cancelled"): {Role.CUSTOMER},
    ("ready_for_delivery", "delivered"): {Role.DEVELOPER},
    ("ready_for_delivery", "cancelled"): {Role.CUSTOMER},
    ("delivered", "completed"): {Role.CUSTOMER},
    ("delivered", "revision_requested"): {Role.CUSTOMER},
}

# Statuses a booking must currently be in for "accept a revision"
# and "submit a delivery" to be valid — used by services.py alongside
# TRANSITIONS so those two multi-field actions (which carry a payload,
# not just a bare status change) still go through the same allowed-set
# check as every other transition.
DELIVERABLE_STATUSES = {"waiting_for_customer", "ready_for_delivery"}
REVISION_REQUESTABLE_STATUSES = {"waiting_for_customer", "delivered"}

TERMINAL_STATUSES = {"completed", "cancelled", "rejected"}


def is_valid_transition(from_code: str, to_code: str) -> bool:
    """Pure adjacency check — does this edge exist at all, regardless
    of who's asking. Admin overrides (see can_transition) are a
    separate, deliberately narrower question: even an admin can't
    invent an edge that isn't in the graph."""
    return to_code in TRANSITIONS.get(from_code, set())


def can_transition(from_code: str, to_code: str, *, role: str) -> bool:
    """Whether `role` may specifically drive this edge. An admin may
    perform any edge that's in the graph at all, even one with no
    entry in TRANSITION_ACTORS (e.g. a support override) — every other
    role is restricted to exactly the actors list says."""
    if not is_valid_transition(from_code, to_code):
        return False
    if role == Role.ADMIN:
        return True
    allowed_roles = TRANSITION_ACTORS.get((from_code, to_code), set())
    return role in allowed_roles


def describe_invalid_transition(from_code: str, to_code: str) -> str:
    if to_code not in TRANSITIONS and to_code not in TERMINAL_STATUSES:
        return f"Unknown status code: {to_code!r}"
    if from_code in TERMINAL_STATUSES:
        return f"This project's status is final and cannot be changed further."
    return f"Cannot move a project from {from_code!r} to {to_code!r} directly."