from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware

from bookmarks.models import UserProfile, GlobalSettings


class CustomRemoteUserMiddleware(RemoteUserMiddleware):
    header = settings.LD_AUTH_PROXY_USERNAME_HEADER


default_global_settings = GlobalSettings()

standard_profile = UserProfile()
standard_profile.enable_favicons = True
standard_profile.ai_api_key = ""
standard_profile.ai_model = ""
standard_profile.ai_tag_vocabulary = ""


class LinkdingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # add global settings to request
        try:
            global_settings = GlobalSettings.get()
        except:
            global_settings = default_global_settings
        request.global_settings = global_settings

        # add user profile to request
        if request.user.is_authenticated:
            request.user_profile = request.user.profile
        else:
            # check if a custom profile for guests exists, otherwise use standard profile
            if global_settings.guest_profile_user:
                request.user_profile = global_settings.guest_profile_user.profile
            else:
                request.user_profile = standard_profile

        response = self.get_response(request)

        return response
