from django.apps import AppConfig


class ConfigurationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.configuration"
    verbose_name = "Site Configuration"

    def ready(self):
        # Registers the post_save cache-invalidation receivers — see
        # signals.py for why this has to happen here rather than at
        # import time of models.py itself.
        from . import signals  # noqa: F401
