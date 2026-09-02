"""
Every rupees<->paise conversion and every advance/final split in this
app goes through here — nowhere else. The spec is explicit about this
twice ("centralized... do NOT duplicate these calculations") and for
good reason: two slightly different rounding implementations for the
same 50/50 split is exactly how a payments system ends up a paisa off
between what the frontend displays and what Razorpay actually charged.

Never floats. Every function here takes and returns Decimal (rupees)
or int (paise) — never float — because float can't represent most
decimal fractions exactly (0.1 + 0.2 != 0.3 in IEEE 754), which is
disqualifying for money.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# The one rounding rule used everywhere in this app. ROUND_HALF_UP
# (round 0.5 away from zero) rather than Decimal's own default,
# ROUND_HALF_EVEN ("banker's rounding") — half-up is what a customer
# or an auditor actually expects when they see ₹499.995 become
# ₹500.00, and using one fixed rule everywhere is the only way two
# numbers that are supposed to add up to a total actually do.
_CENTS = Decimal("0.01")

# Razorpay's smallest-unit multiplier for INR: ₹1 = 100 paise. If this
# app ever needs to support a currency with a different subunit
# ratio, this is the one place that changes.
PAISE_PER_RUPEE = 100


def round_money(amount: Decimal) -> Decimal:
    """Round to 2 decimal places using the app's one fixed rule."""
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


def to_paise(amount: Decimal) -> int:
    """Rupees -> the integer paise Razorpay's Orders API expects."""
    return int(round_money(amount) * PAISE_PER_RUPEE)


def from_paise(paise: int) -> Decimal:
    """Paise -> rupees, for displaying or storing what Razorpay sent back."""
    return round_money(Decimal(paise) / PAISE_PER_RUPEE)


def split_advance_and_final(total: Decimal, *, advance_percent: Decimal = Decimal("50")) -> tuple[Decimal, Decimal]:
    """
    The one place the 50/50 (or, if a future part makes the split
    admin-configurable, whatever/whatever) split happens. Rounds the
    advance amount, then derives the final amount as `total -
    advance` rather than independently rounding both halves — that's
    what guarantees advance + final always equals total exactly, even
    when the total doesn't split evenly (₹999.99 split by two rounded
    independently could drift a paisa; subtraction can't).
    """
    advance = round_money(total * advance_percent / Decimal("100"))
    final = round_money(total - advance)
    return advance, final