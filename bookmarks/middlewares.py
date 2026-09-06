from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.utils import translation

from bookmarks.models import GlobalSettings, UserProfile


class CustomRemoteUserMiddleware(RemoteUserMiddleware):
    header = settings.LD_AUTH_PROXY_USERNAME_HEADER


default_global_settings = GlobalSettings()

standard_profile = UserProfile()
standard_profile.enable_favicons = True


class LinkdingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # add global settings to request
        try:
            global_settings = GlobalSettings.get()
        except Exception:
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


class UserLanguageMiddleware:
    """
    Activates the language chosen in the user profile. Must run after Django's
    LocaleMiddleware, which handles the browser language, and after
    LinkdingMiddleware, which provides request.user_profile.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = getattr(request.user_profile, "language", "")
        if language and language in dict(settings.LANGUAGES):
            translation.activate(language)
            request.LANGUAGE_CODE = translation.get_language()

        return self.get_response(request)
