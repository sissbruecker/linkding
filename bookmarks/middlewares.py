import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers

from bookmarks.models import GlobalSettings, UserProfile

logger = logging.getLogger(__name__)


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


class CorsMiddleware:
    """
    Adds CORS headers to API responses for origins configured through
    LD_CORS_ALLOWED_ORIGINS, and answers preflight requests before they reach
    the API views, which would otherwise reject them as unauthenticated.
    Credentials are never allowed, so cross-origin requests have to
    authenticate with an API token.

    Removes itself from the middleware chain if no valid origins are configured.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.api_path = "/" + settings.LD_CONTEXT_PATH + "api/"
        self.allowed_origins = set()
        for origin in settings.LD_CORS_ALLOWED_ORIGINS.split(","):
            origin = origin.strip()
            if not origin:
                continue
            parsed = self.parse_origin(origin)
            if parsed:
                self.allowed_origins.add(parsed)
            else:
                logger.warning(
                    "Ignoring invalid origin in LD_CORS_ALLOWED_ORIGINS: '%s'. "
                    "Expected format: https://host[:port]",
                    origin,
                )

        if not self.allowed_origins:
            raise MiddlewareNotUsed()

    def __call__(self, request):
        if not request.path.startswith(self.api_path):
            return self.get_response(request)

        is_preflight = (
            request.method == "OPTIONS"
            and "Access-Control-Request-Method" in request.headers
        )
        if is_preflight:
            response = HttpResponse(headers={"Content-Length": "0"})
        else:
            response = self.get_response(request)

        patch_vary_headers(response, ("Origin",))

        origin = request.headers.get("Origin")
        if not origin or self.parse_origin(origin) not in self.allowed_origins:
            return response

        response["Access-Control-Allow-Origin"] = origin
        if is_preflight:
            response["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            )
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response["Access-Control-Max-Age"] = "86400"
        return response

    @staticmethod
    def parse_origin(origin):
        """
        Returns a (scheme, netloc) tuple for a valid origin, or None if the
        value is not a valid origin.
        """
        try:
            url = urlsplit(origin)
        except ValueError:
            return None
        if (
            not url.scheme
            or not url.netloc
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or url.username is not None
        ):
            return None
        return (url.scheme, url.netloc)
