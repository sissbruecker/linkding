"""
Development settings for linkding webapp
"""

# Start from development settings
# noinspection PyUnresolvedReferences
from .base import *

# Turn on debug mode
DEBUG = True

# Enable debug toolbar
# INSTALLED_APPS.append("debug_toolbar")
# MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

INTERNAL_IPS = [
    "127.0.0.1",
]

# Allow access through ngrok
CSRF_TRUSTED_ORIGINS = ["https://*.ngrok-free.app"]

STATICFILES_DIRS = [
    # Resolve theme files from style source folder
    os.path.join(BASE_DIR, "bookmarks", "styles"),
    # Resolve downloaded files in dev environment
    os.path.join(BASE_DIR, "data", "favicons"),
    os.path.join(BASE_DIR, "data", "previews"),
]

# Enable debug logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {asctime} {module}: {message}",
            "style": "{",
        },
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",  # Set to DEBUG to log all SQL calls
            "handlers": ["console"],
        },
        "bookmarks": {  # Log importer debug output
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "huey": {  # Huey
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# Import custom settings
# noinspection PyUnresolvedReferences
from .custom import *
