from urllib.parse import urlparse
from django.conf import settings
from django.core import validators

class BookmarkURLValidator(validators.URLValidator):
    def __init__(self, *args, **kwargs):
        # Allow only http and https and use a clearer error message
        kwargs.setdefault("schemes", ["http", "https"])
        kwargs.setdefault("message", "Only http and https URLs are supported.")
        super().__init__(*args, **kwargs)

    def __call__(self, value):
        if settings.LD_DISABLE_URL_VALIDATION:
            return

        v = (value or "").strip()
        p = urlparse(v)

        # If no scheme and it looks like a domain, assume https for validation
        if not p.scheme and "." in v and " " not in v:
            v = "https://" + v

        # Now validate the normalized value
        super().__call__(v)