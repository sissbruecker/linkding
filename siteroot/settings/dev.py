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

# Enable debug logging
# Logging with SQL statements
LOGGING = {
    'version': 1,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}

# Import custom settings
# noinspection PyUnresolvedReferences
from .custom import *
