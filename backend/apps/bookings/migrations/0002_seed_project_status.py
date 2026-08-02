from django.db import migrations

# (code, label, is_terminal, is_default, color)
STATUSES = [
    ("draft", "Draft", False, True, "gray"),
    ("submitted", "Submitted", False, False, "blue"),
    ("accepted", "Accepted", False, False, "blue"),
    ("rejected", "Rejected", True, False, "red"),
    ("in_progress", "In Progress", False, False, "amber"),
    ("waiting_for_customer", "Waiting For Customer", False, False, "amber"),
    ("delivered", "Delivered", False, False, "teal"),
    ("completed", "Completed", True, False, "green"),
    ("cancelled", "Cancelled", True, False, "red"),
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


def remove_statuses(apps, schema_editor):
    ProjectStatus = apps.get_model("bookings", "ProjectStatus")
    ProjectStatus.objects.filter(code__in=[s[0] for s in STATUSES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_statuses, remove_statuses),
    ]