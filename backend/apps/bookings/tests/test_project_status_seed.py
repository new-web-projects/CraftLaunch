from django.test import TestCase

from apps.bookings.models import ProjectStatus


class ProjectStatusSeedTests(TestCase):
    """The migration seed, not a fixture — this runs against whatever
    migrations actually produced, so it fails if 0002_seed_project_status
    or 0004_seed_lifecycle_statuses ever silently stops applying.

    Part 5 extends the original 9 statuses to the spec's full 12-state
    machine (apps/bookings/lifecycle.py) via an additive migration
    (0004) rather than editing the already-applied 0002 — so this
    test's expectations grow to 12 codes here, not because the original
    9 broke, but because there are legitimately 3 more of them now."""

    EXPECTED_CODES = {
        "draft",
        "submitted",
        "awaiting_developer",
        "accepted",
        "rejected",
        "in_progress",
        "waiting_for_customer",
        "revision_requested",
        "ready_for_delivery",
        "delivered",
        "completed",
        "cancelled",
    }

    def test_all_twelve_statuses_exist(self):
        codes = set(ProjectStatus.objects.values_list("code", flat=True))
        self.assertEqual(codes, self.EXPECTED_CODES)

    def test_exactly_one_default_status(self):
        self.assertEqual(ProjectStatus.objects.filter(is_default=True).count(), 1)
        self.assertEqual(ProjectStatus.get_default().code, "draft")

    def test_terminal_statuses(self):
        terminal_codes = set(ProjectStatus.objects.filter(is_terminal=True).values_list("code", flat=True))
        self.assertEqual(terminal_codes, {"rejected", "completed", "cancelled"})

    def test_statuses_are_ordered(self):
        codes_in_order = list(ProjectStatus.objects.values_list("code", flat=True))
        self.assertEqual(codes_in_order[0], "draft")
        self.assertEqual(codes_in_order[-1], "rejected")