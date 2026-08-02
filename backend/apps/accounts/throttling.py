from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """
    Applied only to the login view, on top of the global anon/user
    throttle rates. Keyed by the attempted `identifier` (email or
    username) when present, falling back to IP — so credential
    stuffing against one account gets slowed down even from many
    different IPs, without also penalizing every other user behind the
    same NAT'd/office IP.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        try:
            identifier = str(request.data.get("identifier", "")).strip().lower()
        except Exception:
            identifier = ""
        ident = identifier or self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}