"""
Cached read path for every configuration singleton. A settings row is
read on nearly every request (site branding on every page, feature
flags gating registration, SEO tags on every response) but written
rarely (an admin saving a form) — caching the read and invalidating on
write is the right trade-off, not caching at all would mean a database
round trip per request for values that almost never change.

Cache invalidation is signal-driven (signals.py posts a `cache.delete`
on every save of these models) rather than this module owning both
directions itself, so any future write path — Django admin, a
management command, the eventual admin-panel API — gets correct
invalidation for free without having to remember to call these
functions' invalidate step. CONFIG_CACHE_TTL below is a safety net on
top of that, not the primary invalidation mechanism: signal delivery
is in-process, but every environment that matters (production, and
development whenever REDIS_URL is set — see config/settings/*.py's
CACHES blocks) shares one Redis cache across all workers/processes, so
a save in one worker correctly invalidates the read in every other
worker. The TTL only matters if a row is ever changed through a path
that bypasses .save() (bulk .update(), a direct SQL write) — for a
SingletonModel with exactly one row, that shouldn't come up, but
letting a stale cache entry self-heal within the hour costs nothing.
"""

from django.core.cache import cache

from .models import (
    EmailConfiguration,
    FeatureFlags,
    PaymentConfiguration,
    SEOConfiguration,
    SiteConfiguration,
    StorageConfiguration,
)

CONFIG_CACHE_TTL = 3600  # seconds; see module docstring

CACHE_KEYS = {
    SiteConfiguration: "configuration:site",
    SEOConfiguration: "configuration:seo",
    StorageConfiguration: "configuration:storage",
    EmailConfiguration: "configuration:email",
    PaymentConfiguration: "configuration:payment",
    FeatureFlags: "configuration:feature_flags",
}


def _get_cached(model):
    key = CACHE_KEYS[model]
    instance = cache.get(key)
    if instance is None:
        instance = model.load()
        cache.set(key, instance, CONFIG_CACHE_TTL)
    return instance


def invalidate(model):
    """Called by signals.py on every save — also exported so tests
    (and any future management command that writes these rows
    directly) can force a fresh read without waiting on TTL."""
    cache.delete(CACHE_KEYS[model])


def get_site_configuration() -> SiteConfiguration:
    return _get_cached(SiteConfiguration)


def get_seo_configuration() -> SEOConfiguration:
    return _get_cached(SEOConfiguration)


def get_storage_configuration() -> StorageConfiguration:
    return _get_cached(StorageConfiguration)


def get_email_configuration() -> EmailConfiguration:
    return _get_cached(EmailConfiguration)


def get_payment_configuration() -> PaymentConfiguration:
    return _get_cached(PaymentConfiguration)


def get_feature_flags() -> FeatureFlags:
    return _get_cached(FeatureFlags)
