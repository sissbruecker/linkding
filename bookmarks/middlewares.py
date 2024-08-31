from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware

from bookmarks.models import UserProfile, GlobalSettings


class CustomRemoteUserMiddleware(RemoteUserMiddleware):
    header = settings.LD_AUTH_PROXY_USERNAME_HEADER


standard_profile = UserProfile()
standard_profile.enable_favicons = True


class UserProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user_profile = request.user.profile
        else:
            # check if a custom profile for guests exists, otherwise use standard profile
            guest_profile = None
            try:
                global_settings = GlobalSettings.get()
                if global_settings.guest_profile_user:
                    guest_profile = global_settings.guest_profile_user.profile
            except:
                pass

            request.user_profile = guest_profile or standard_profile

        response = self.get_response(request)

        return response
