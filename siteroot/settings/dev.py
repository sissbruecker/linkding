"""
Development settings for linkding webapp
"""

# Start from development settings
# noinspection PyUnresolvedReferences
from .base import *

# Turn on debug mode
DEBUG = True
# Turn on SASS compilation
SASS_PROCESSOR_ENABLED = True

# Enable debug toolbar
INSTALLED_APPS.append('debug_toolbar')
MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

INTERNAL_IPS = [
    '127.0.0.1',
]

# Enable debug logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',  # Set to DEBUG to log all SQL calls
            'handlers': ['console'],
        },
        'bookmarks.services.tasks': {  # Log task output
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        }
    }
}

# Import custom settings
# noinspection PyUnresolvedReferences
from .custom import *
