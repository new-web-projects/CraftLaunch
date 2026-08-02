from django.test import TestCase

from apps.bookings.models import ProjectStatus


class ProjectStatusSeedTests(TestCase):
    """The migration seed, not a fixture — this runs against whatever
    migrations actually produced, so it fails if 0002_seed_project_status
    ever silently stops applying."""

    EXPECTED_CODES = {
        "draft",
        "submitted",
        "accepted",
        "rejected",
        "in_progress",
        "waiting_for_customer",
        "delivered",
        "completed",
        "cancelled",
    }

    def test_all_nine_statuses_exist(self):
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
        self.assertEqual(codes_in_order[-1], "cancelled")