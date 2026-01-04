"""
Stuff in here is only used for type hints
"""

from django import http
from django.contrib.auth.models import AnonymousUser

from bookmarks.models import GlobalSettings, User, UserProfile


class HttpRequest(http.HttpRequest):
    global_settings: GlobalSettings
    user_profile: UserProfile
    user: User | AnonymousUser
