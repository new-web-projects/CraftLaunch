from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

API_VERSION = "0.1.0"


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Liveness endpoint. No database access, no auth required — this
    should stay reachable even if the database is briefly down, since
    it's what uptime monitors, orchestrators and the frontend's status
    widget all poll first.
    """
    return Response(
        {
            "status": "ok",
            "service": "craftlaunch-api",
            "version": API_VERSION,
        }
    )
