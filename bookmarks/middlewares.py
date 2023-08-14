from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware

from bookmarks.models import UserProfile


class CustomRemoteUserMiddleware(RemoteUserMiddleware):
    header = settings.LD_AUTH_PROXY_USERNAME_HEADER


class UserProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user_profile = request.user.profile
        else:
            request.user_profile = UserProfile()
            request.user_profile.enable_favicons = True

        response = self.get_response(request)

        return response
