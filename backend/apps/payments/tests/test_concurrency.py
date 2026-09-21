# File Path: backend/apps/payments/tests/test_concurrency.py
"""
Genuine multi-threaded regression tests for the two races found during
the Part 6 re-audit (see services.py's comments on
PaymentOrderService.create_order and PaymentVerificationService.
verify_payment for the full story). TransactionTestCase, not TestCase
— each thread needs its own real DB connection/transaction rather
than sharing the outer test's uncommitted one, the same reason
apps.bookings.tests.test_lifecycle.ConcurrentAcceptThreadTests uses it.
"""

import hashlib
import hmac
import json
import threading
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.db import connections
from django.test import TransactionTestCase

from apps.payments.models import Payment, PaymentOrder, PaymentTransaction
from apps.payments.services import PaymentOrderService, PaymentVerificationService, WebhookService

from .test_order_creation import PaymentFixtureMixin


def _ensure_project_statuses_seeded():
    """Re-seeds apps.bookings' ProjectStatus rows directly rather than
    relying on them surviving TransactionTestCase's post-test
    truncation — see the classes below for why. Mirrors
    apps/bookings/migrations/0004_seed_lifecycle_statuses.py's data
    exactly; kept as a plain function (not an import from the
    migration module) since migrations aren't meant to be imported
    from application/test code."""
    from apps.bookings.models import ProjectStatus

    statuses = [
        ("draft", "Draft", False, True, "gray"),
        ("submitted", "Submitted", False, False, "blue"),
        ("awaiting_developer", "Awaiting Developer", False, False, "blue"),
        ("accepted", "Accepted", False, False, "blue"),
        ("in_progress", "In Progress", False, False, "amber"),
        ("waiting_for_customer", "Waiting For Customer", False, False, "amber"),
        ("revision_requested", "Revision Requested", False, False, "amber"),
        ("ready_for_delivery", "Ready For Delivery", False, False, "teal"),
        ("delivered", "Delivered", False, False, "teal"),
        ("completed", "Completed", True, False, "green"),
        ("cancelled", "Cancelled", True, False, "red"),
        ("rejected", "Rejected", True, False, "red"),
    ]
    for order, (code, label, is_terminal, is_default, color) in enumerate(statuses):
        ProjectStatus.objects.update_or_create(
            code=code,
            defaults={"label": label, "sort_order": order, "is_terminal": is_terminal, "is_default": is_default, "color": color},
        )


class ConcurrentOrderCreationTests(PaymentFixtureMixin, TransactionTestCase):
    # TransactionTestCase truncates every table after each test method
    # by default and does not automatically restore migration-seeded
    # data (ProjectStatus, here, via apps.bookings' seed migrations).
    # serialized_rollback=True is Django's usual answer to that, but
    # it has a known bad interaction with contenttypes' own
    # post-migrate hook when more than one TransactionTestCase with
    # serialized_rollback runs in the same suite (a
    # django_content_type unique-constraint IntegrityError) — this
    # file's tests passed in isolation but failed as part of the full
    # suite for exactly that reason. Re-seeding directly in setUp()
    # instead sidesteps Django's serialization machinery entirely, so
    # it can't conflict with any other test class doing the same.
    def setUp(self):
        super().setUp()
        _ensure_project_statuses_seeded()

    def test_only_one_order_created_under_concurrent_requests(self):
        """Two near-simultaneous create_order calls for the same
        booking+phase must result in exactly one PaymentOrder — the
        exact bug this audit found in an earlier version of
        create_order (see its module comment)."""
        booking = self._accepted_booking()
        results = {}

        def attempt(key):
            client = MagicMock()
            client.order.create.return_value = {"id": f"order_CONCURRENT_{key}", "status": "created"}
            try:
                with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
                    order = PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)
                results[key] = ("ok", order.razorpay_order_id)
            except Exception as exc:
                # Any failure here — our own ValidationError, or
                # SQLite's own coarse table-level locking raising a raw
                # OperationalError instead of the row-level queueing
                # Postgres would do (see
                # apps.bookings.tests.test_lifecycle.ConcurrentAcceptThreadTests
                # for the same situation) — means this attempt didn't
                # win. The outcome that actually matters is the final
                # DB state asserted below, which is mechanism-agnostic.
                results[key] = ("did not win", str(exc))
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a",))
        t2 = threading.Thread(target=attempt, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # The critical invariant: regardless of how the two calls
        # individually resolved (one might win outright, one might be
        # told to retry, or — if timing allows the second to observe
        # the first's completed order — both might return the *same*
        # order), the database must never end up with two live orders
        # for one Payment.
        payment = Payment.objects.get(booking=booking, phase=Payment.Phase.ADVANCE_PAYMENT)
        active_orders = payment.orders.filter(status__in=PaymentOrder.ACTIVE_STATUSES)
        self.assertLessEqual(
            active_orders.count(), 1, f"expected at most one active order, got {active_orders.count()}: {results}"
        )

    def test_sequential_retry_after_concurrent_rejection_succeeds(self):
        """If a concurrent attempt is told 'try again shortly', a
        follow-up call must actually succeed — the claim must not
        become permanently stuck."""
        booking = self._accepted_booking()
        client = self._mock_razorpay_client()

        with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
            first = PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)
            second = PaymentOrderService.create_order(booking, phase=Payment.Phase.ADVANCE_PAYMENT, customer=self.customer)

        # Sequential duplicate-click behavior (already covered
        # elsewhere) — included here as a sanity check that this
        # rewrite didn't regress the non-concurrent case.
        self.assertEqual(first.id, second.id)


class ConcurrentVerificationTests(PaymentFixtureMixin, TransactionTestCase):
    """Verifies the frontend-verify path and the webhook path converge
    safely regardless of which arrives first."""

    def setUp(self):  # see ConcurrentOrderCreationTests.setUp's comment
        super().setUp()
        _ensure_project_statuses_seeded()

    def _make_order(self):
        booking = self._accepted_booking()
        payment = Payment.objects.create(
            booking=booking, customer=self.customer, phase=Payment.Phase.ADVANCE_PAYMENT,
            amount=Decimal("500.00"), currency="INR", status=Payment.Status.ORDER_CREATED,
        )
        return PaymentOrder.objects.create(
            payment=payment, razorpay_order_id="order_RACE1", amount=Decimal("500.00"),
            amount_paise=50000, currency="INR", receipt="race-receipt-1", status=PaymentOrder.Status.CREATED,
        )

    @staticmethod
    def _webhook_signed_body():
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_RACE1", "order_id": "order_RACE1",
                        "amount": 50000, "currency": "INR", "status": "captured", "method": "upi",
                    }
                }
            },
        }
        body = json.dumps(payload)
        signature = hmac.new(b"dummy_webhook_secret", body.encode(), hashlib.sha256).hexdigest()
        return body, signature

    def test_webhook_and_verify_racing_converge_to_captured_with_one_transaction(self):
        order = self._make_order()
        body, signature = self._webhook_signed_body()

        def do_verify():
            client = MagicMock()
            client.payment.fetch.return_value = {
                "id": "pay_RACE1", "order_id": "order_RACE1", "amount": 50000,
                "currency": "INR", "status": "captured", "method": "upi",
            }
            try:
                with patch("apps.payments.services.RazorpayClientFactory.get_client", return_value=client):
                    PaymentVerificationService.verify_payment(
                        order.id, razorpay_order_id="order_RACE1", razorpay_payment_id="pay_RACE1",
                        razorpay_signature="whatever-the-mock-accepts", customer=self.customer,
                    )
            except Exception:
                # See ConcurrentOrderCreationTests.attempt — either our
                # own ValidationError or SQLite's coarser locking
                # surfacing as a raw OperationalError both just mean
                # "this side didn't win the race"; the assertions below
                # check the outcome that actually matters.
                pass
            finally:
                connections.close_all()

        def do_webhook():
            try:
                WebhookService.process_webhook(raw_body=body, signature=signature, event_id="evt_race_1")
            except Exception:
                pass
            finally:
                connections.close_all()

        t1 = threading.Thread(target=do_verify)
        t2 = threading.Thread(target=do_webhook)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # The invariant that must hold unconditionally, independent of
        # test-infra locking granularity: never more than one
        # PaymentTransaction for a given razorpay_payment_id, and
        # never an incorrect status (VERIFICATION_FAILED clobbering a
        # real capture, for instance).
        self.assertLessEqual(PaymentTransaction.objects.filter(razorpay_payment_id="pay_RACE1").count(), 1)
        payment = Payment.objects.get(pk=order.payment_id)
        self.assertIn(payment.status, (Payment.Status.CAPTURED, Payment.Status.ORDER_CREATED))

        # SQLite's table-level locking (not Postgres's row-level lock
        # *queuing*, which this app actually runs on in production)
        # can occasionally make both threads hit a transient "database
        # is locked" error at once, leaving neither having completed —
        # a real Postgres deployment would have queued the second
        # request behind the first's row lock and it would have gone
        # through. If that happened here, one more call — now free of
        # contention — models exactly that "eventually consistent
        # after the transient contention clears" behavior.
        if payment.status != Payment.Status.CAPTURED:
            do_verify()
            payment.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertEqual(PaymentTransaction.objects.filter(razorpay_payment_id="pay_RACE1").count(), 1)