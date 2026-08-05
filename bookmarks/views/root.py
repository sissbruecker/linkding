from django.urls import reverse

from bookmarks.models import GlobalSettings
from bookmarks.utils import redirect_with_query


def root(request):
    # Redirect unauthenticated users to the shared bookmarks page if that is
    # the configured landing page
    if not request.user.is_authenticated:
        settings = request.global_settings

        if settings.landing_page == GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS:
            # Retain the query string
            return redirect_with_query(request, reverse("linkding:bookmarks.shared"))

    # Otherwise redirect to the bookmarks page, retaining the query string.
    return redirect_with_query(request, reverse("linkding:bookmarks.index"))
