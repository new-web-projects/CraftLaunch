"""
Pure unit tests — no database, no mocking. money.py is deliberately
side-effect-free, so these test the actual arithmetic directly.
"""

from decimal import Decimal

from django.test import SimpleTestCase

from apps.payments.money import from_paise, round_money, split_advance_and_final, to_paise


class RoundMoneyTests(SimpleTestCase):
    def test_rounds_to_two_decimal_places(self):
        self.assertEqual(round_money(Decimal("100.005")), Decimal("100.01"))

    def test_half_up_not_banker_rounding(self):
        # Decimal's own default (ROUND_HALF_EVEN) would round 0.5 to
        # the nearest *even* digit — 2.5 -> 2, not 3. This app always
        # uses ROUND_HALF_UP instead, so 2.505 rounds up to 2.51, not
        # down to 2.50 the way banker's rounding would take it.
        self.assertEqual(round_money(Decimal("2.505")), Decimal("2.51"))

    def test_exact_values_are_unchanged(self):
        self.assertEqual(round_money(Decimal("499.99")), Decimal("499.99"))


class PaiseConversionTests(SimpleTestCase):
    def test_to_paise_basic(self):
        self.assertEqual(to_paise(Decimal("500.00")), 50000)

    def test_to_paise_with_cents(self):
        self.assertEqual(to_paise(Decimal("499.99")), 49999)

    def test_to_paise_rounds_first(self):
        self.assertEqual(to_paise(Decimal("100.005")), 10001)  # rounds to 100.01 first

    def test_to_paise_returns_int_not_float(self):
        result = to_paise(Decimal("10.00"))
        self.assertIsInstance(result, int)

    def test_from_paise_basic(self):
        self.assertEqual(from_paise(50000), Decimal("500.00"))

    def test_round_trip(self):
        original = Decimal("1234.56")
        self.assertEqual(from_paise(to_paise(original)), original)

    def test_from_paise_returns_decimal_not_float(self):
        result = from_paise(50000)
        self.assertIsInstance(result, Decimal)


class SplitAdvanceAndFinalTests(SimpleTestCase):
    def test_even_split(self):
        advance, final = split_advance_and_final(Decimal("1000.00"))
        self.assertEqual(advance, Decimal("500.00"))
        self.assertEqual(final, Decimal("500.00"))

    def test_split_always_sums_to_total_even_with_odd_cents(self):
        # The case that would drift a paisa if advance and final were
        # each rounded independently instead of final = total - advance.
        total = Decimal("999.99")
        advance, final = split_advance_and_final(total)
        self.assertEqual(advance + final, total)

    def test_split_with_odd_total_favors_advance_on_the_half_paisa(self):
        total = Decimal("999.99")
        advance, final = split_advance_and_final(total)
        # 999.99 / 2 = 499.995 -> rounds up (half-up) to 500.00
        self.assertEqual(advance, Decimal("500.00"))
        self.assertEqual(final, Decimal("499.99"))

    def test_custom_percent_split(self):
        advance, final = split_advance_and_final(Decimal("1000.00"), advance_percent=Decimal("30"))
        self.assertEqual(advance, Decimal("300.00"))
        self.assertEqual(final, Decimal("700.00"))
        self.assertEqual(advance + final, Decimal("1000.00"))

    def test_returns_decimals(self):
        advance, final = split_advance_and_final(Decimal("500.00"))
        self.assertIsInstance(advance, Decimal)
        self.assertIsInstance(final, Decimal)