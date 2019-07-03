"""
Production settings for linkding webapp
"""

# Start from development settings
# noinspection PyUnresolvedReferences
from .settings import *

# Turn of debug mode
DEBUG = False
# Turn off SASS compilation
SASS_PROCESSOR_ENABLED = False

ALLOWED_HOSTS = ['*']

# Import custom settings
# noinspection PyUnresolvedReferences
from .settings_custom import *
