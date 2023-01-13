from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.http import JsonResponse
from django.db import connections
from bookmarks.views.settings import app_version

class CustomRemoteUserMiddleware(RemoteUserMiddleware):
    header = settings.LD_AUTH_PROXY_USERNAME_HEADER

class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/health':
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
        
        return self.get_response(request)