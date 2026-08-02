from django.db import migrations
from django.utils.text import slugify

SERVICE_CATEGORIES = ["New Website", "Website Redesign", "Bug Fixing", "Maintenance"]

WEBSITE_CATEGORIES = ["E-commerce", "Portfolio", "Corporate", "Blog", "Educational", "Non-profit"]

WEBSITE_TYPES = ["Landing Page", "Multi-page Website", "Web Application", "E-commerce Store"]

TECHNOLOGIES = ["React", "Next.js", "Django", "WordPress", "Shopify", "Webflow"]

TAGS = ["popular", "fast-delivery", "seo-optimized", "mobile-first"]

WEBSITE_FEATURES = [
    "Contact Form", "Blog", "Payment Gateway", "Newsletter Signup",
    "Multi-language Support", "Live Chat", "SEO Package", "User Accounts",
    "Search Functionality", "Booking/Scheduling",
]


def seed_catalog(apps, schema_editor):
    ServiceCategory = apps.get_model("catalog", "ServiceCategory")
    WebsiteCategory = apps.get_model("catalog", "WebsiteCategory")
    WebsiteType = apps.get_model("catalog", "WebsiteType")
    Technology = apps.get_model("catalog", "Technology")
    Tag = apps.get_model("catalog", "Tag")
    WebsiteFeature = apps.get_model("catalog", "WebsiteFeature")

    for model, names in [
        (ServiceCategory, SERVICE_CATEGORIES),
        (WebsiteCategory, WEBSITE_CATEGORIES),
        (WebsiteType, WEBSITE_TYPES),
        (Technology, TECHNOLOGIES),
        (Tag, TAGS),
        (WebsiteFeature, WEBSITE_FEATURES),
    ]:
        for order, name in enumerate(names):
            model.objects.update_or_create(
                slug=slugify(name), defaults={"name": name, "sort_order": order}
            )


def remove_seed(apps, schema_editor):
    ServiceCategory = apps.get_model("catalog", "ServiceCategory")
    WebsiteCategory = apps.get_model("catalog", "WebsiteCategory")
    WebsiteType = apps.get_model("catalog", "WebsiteType")
    Technology = apps.get_model("catalog", "Technology")
    Tag = apps.get_model("catalog", "Tag")
    WebsiteFeature = apps.get_model("catalog", "WebsiteFeature")

    for model, names in [
        (ServiceCategory, SERVICE_CATEGORIES),
        (WebsiteCategory, WEBSITE_CATEGORIES),
        (WebsiteType, WEBSITE_TYPES),
        (Technology, TECHNOLOGIES),
        (Tag, TAGS),
        (WebsiteFeature, WEBSITE_FEATURES),
    ]:
        model.objects.filter(slug__in=[slugify(n) for n in names]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, remove_seed),
    ]