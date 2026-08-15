from django.db.models.signals import post_save
from django.dispatch import receiver

from . import services
from .models import (
    EmailConfiguration,
    FeatureFlags,
    PaymentConfiguration,
    SEOConfiguration,
    SiteConfiguration,
    StorageConfiguration,
)

_MODELS = (
    SiteConfiguration,
    SEOConfiguration,
    StorageConfiguration,
    EmailConfiguration,
    PaymentConfiguration,
    FeatureFlags,
)


def _invalidate(sender, **kwargs):
    services.invalidate(sender)


for _model in _MODELS:
    post_save.connect(_invalidate, sender=_model, weak=False)
