from django.db import connections
from django.http import JsonResponse

from bookmarks.views.settings import app_version


def health(request):
    code = 200
    response = {"version": app_version, "status": "healthy"}

    try:
        connections["default"].ensure_connection()
    except Exception:
        response["status"] = "unhealthy"
        code = 500

    return JsonResponse(response, status=code)
