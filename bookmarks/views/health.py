from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.http import JsonResponse
from django.db import connections
from bookmarks.views.settings import app_version

def health(request):
    code = 200
    response = {
        'version': app_version,
        'status': 'healthy'
        }

    try:
        connections['default'].ensure_connection()
    except Exception as e:
        response['status'] = 'unhealthy'
        code = 500

    return JsonResponse(response, status=code)