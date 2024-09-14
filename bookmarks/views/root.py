from django.http import HttpResponseRedirect
from django.urls import reverse

from bookmarks.models import GlobalSettings


def root(request):
    # Redirect unauthenticated users to the configured landing page
    if not request.user.is_authenticated:
        settings = request.global_settings

        if settings.landing_page == GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS:
            return HttpResponseRedirect(reverse("bookmarks:shared"))
        else:
            return HttpResponseRedirect(reverse("login"))

    # Redirect authenticated users to the bookmarks page
    return HttpResponseRedirect(reverse("bookmarks:index"))
