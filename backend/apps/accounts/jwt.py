from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserSession


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def issue_tokens_for_user(user, request, remember_me: bool = False) -> RefreshToken:
    """
    Mints a refresh+access pair, stamps custom claims (role, username —
    so the frontend doesn't need a round trip just to know the role),
    applies the "remember me" lifetime, and records a UserSession row
    so this login shows up in the user's active-sessions list.
    """
    refresh = RefreshToken.for_user(user)

    if remember_me:
        refresh.set_exp(lifetime=settings.JWT_REFRESH_TOKEN_LIFETIME_REMEMBER_ME)

    # Stored as a claim (not just used once at issuance) so RefreshView
    # can preserve it across rotations — otherwise a "remembered" login
    # would silently drop back to a short-lived session on its first refresh.
    refresh["remember_me"] = remember_me

    for token in (refresh, refresh.access_token):
        token["role"] = user.role
        token["username"] = user.username

    UserSession.objects.create(
        user=user,
        jti=str(refresh["jti"]),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        ip_address=client_ip(request),
    )

    return refresh