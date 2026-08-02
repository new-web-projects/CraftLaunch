from django.conf import settings
from django.core.mail import send_mail

from .tokens import email_verification_token, encode_uid, password_reset_token


def _frontend_link(path: str, **params) -> str:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}?{query}"


def send_verification_email(user) -> None:
    uid = encode_uid(user.pk)
    token = email_verification_token.make_token(user)
    link = _frontend_link("/verify-email", uid=uid, token=token)

    send_mail(
        subject=f"Verify your {settings.SITE_NAME} email",
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
        subject=f"Reset your {settings.SITE_NAME} password",
        message=(
            f"Hi {user.username},\n\n"
            f"Use this link to set a new password (valid for a limited time):\n{link}\n\n"
            f"If you didn't request this, you can ignore this email — your "
            f"password won't change."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )