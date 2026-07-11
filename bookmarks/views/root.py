from django.http import HttpResponseRedirect
from django.urls import reverse

from bookmarks.models import GlobalSettings
from bookmarks.utils import redirect_with_query


def root(request):
    # Redirect unauthenticated users to the configured landing page
    if not request.user.is_authenticated:
        settings = request.global_settings

        if settings.landing_page == GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS:
            # Retain the query string so that deep links (e.g. ?q=<tag>) work
            return redirect_with_query(request, reverse("linkding:bookmarks.shared"))
        else:
            return HttpResponseRedirect(reverse("login"))

    # Redirect authenticated users to the bookmarks page, retaining the query
    # string so that deep links (e.g. ?q=<tag>) work
    return redirect_with_query(request, reverse("linkding:bookmarks.index"))
