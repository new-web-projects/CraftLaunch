from django.conf import settings


def set_refresh_cookie(response, token: str, remember_me: bool = False) -> None:
    """
    The refresh token itself is httpOnly — invisible to JS, so an XSS
    bug can't exfiltrate it. A second, non-httpOnly "hint" cookie
    (just the string "1", nothing sensitive) is set alongside it so
    the Next.js middleware can make a fast, non-authoritative
    redirect decision without ever touching the real token; the
    frontend's silent-refresh call is what actually validates a session.

    When remember_me is False, both cookies are session cookies (no
    max_age) and disappear when the browser closes, on top of the
    refresh token itself carrying a shorter expiry — belt and braces.
    """
    max_age = (
        int(settings.JWT_REFRESH_TOKEN_LIFETIME_REMEMBER_ME.total_seconds())
        if remember_me
        else None
    )

    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/api/auth/",
        max_age=max_age,
    )
    response.set_cookie(
        key=settings.AUTH_SESSION_HINT_COOKIE_NAME,
        value="1",
        httponly=False,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
        max_age=max_age,
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(settings.AUTH_REFRESH_COOKIE_NAME, path="/api/auth/")
    response.delete_cookie(settings.AUTH_SESSION_HINT_COOKIE_NAME, path="/")