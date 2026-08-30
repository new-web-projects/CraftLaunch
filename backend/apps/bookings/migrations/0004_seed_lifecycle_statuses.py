from django.db import migrations

# Part 5 needs 3 statuses Part 3 didn't seed yet (see lifecycle.py's
# TRANSITIONS graph). Rather than edit 0002_seed_project_status.py —
# already-applied migrations shouldn't be rewritten — this adds the
# missing 3 and reasserts sort_order for the *complete* set of 12, so
# the full lifecycle orders correctly end to end. update_or_create on
# `code` makes this safe to run against a database that already has
# the original 9 rows (the normal case) or, in a fresh environment,
# against none at all.
#
# (code, label, is_terminal, is_default, color)
STATUSES = [
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


def seed_statuses(apps, schema_editor):
    ProjectStatus = apps.get_model("bookings", "ProjectStatus")
    for order, (code, label, is_terminal, is_default, color) in enumerate(STATUSES):
        ProjectStatus.objects.update_or_create(
            code=code,
            defaults={
                "label": label,
                "sort_order": order,
                "is_terminal": is_terminal,
                "is_default": is_default,
                "color": color,
            },
        )


def remove_added_statuses(apps, schema_editor):
    ProjectStatus = apps.get_model("bookings", "ProjectStatus")
    ProjectStatus.objects.filter(
        code__in=["awaiting_developer", "revision_requested", "ready_for_delivery"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0003_part5_lifecycle"),
    ]

    operations = [
        migrations.RunPython(seed_statuses, remove_added_statuses),
    ]