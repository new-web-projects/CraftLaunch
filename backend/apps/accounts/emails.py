from django.conf import settings
from django.core.mail import send_mail

from .tokens import email_verification_token, encode_uid, password_reset_token


def _site_name() -> str:
    """Part 4 made the website name admin-configurable
    (apps/configuration/models.py's SiteConfiguration) — this is the
    first of what should eventually be every user-facing string that
    used to read the static SITE_NAME env var. Falls back to
    settings.SITE_NAME on any failure (e.g. called before the
    configuration app's migration has run) since a subject line
    shouldn't be why a verification email fails to send."""
    try:
        from apps.configuration.services import get_site_configuration

        return get_site_configuration().website_name or settings.SITE_NAME
    except Exception:
        return settings.SITE_NAME


def _frontend_link(path: str, **params) -> str:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}?{query}"


def send_verification_email(user) -> None:
    uid = encode_uid(user.pk)
    token = email_verification_token.make_token(user)
    link = _frontend_link("/verify-email", uid=uid, token=token)

    send_mail(
        subject=f"Verify your {_site_name()} email",
        message=(
            f"Hi {user.username},\n\n"
            f"Confirm your email address to activate your account:\n{link}\n\n"
            f"If you didn't create this account, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def send_password_reset_email(user) -> None:
    uid = encode_uid(user.pk)
    token = password_reset_token.make_token(user)
    link = _frontend_link("/reset-password", uid=uid, token=token)

    send_mail(
        subject=f"Reset your {_site_name()} password",
        message=(
            f"Hi {user.username},\n\n"
            f"Use this link to set a new password (valid for a limited time):\n{link}\n\n"
            f"If you didn't request this, you can ignore this email — your "
            f"password won't change."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )