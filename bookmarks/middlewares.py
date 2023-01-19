from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware

class CustomRemoteUserMiddleware(RemoteUserMiddleware):
    header = settings.LD_AUTH_PROXY_USERNAME_HEADER
