from django.utils.translation import gettext, gettext_noop

from bookmarks import utils
from bookmarks.models import Toast

# Strings that are rendered by the static frontend bundle. The values are
# msgids from the server-side translation catalog, so they are translated with
# the language that is active for the current request.
FRONTEND_STRINGS = {
    "confirm.cancel": gettext_noop("Cancel"),
    "confirm.confirm": gettext_noop("Confirm"),
    "confirm.question": gettext_noop("Are you sure?"),
    "filters.title": gettext_noop("Filters"),
    "filters.close": gettext_noop("Close dialog"),
    "search.tags": gettext_noop("Tags"),
    "search.recentSearches": gettext_noop("Recent Searches"),
    "search.bookmarks": gettext_noop("Bookmarks"),
}


def js_i18n(request):
    return {
        "js_i18n": {
            key: gettext(message) for key, message in FRONTEND_STRINGS.items()
        }
    }


def toasts(request):
    user = request.user
    toast_messages = (
        Toast.objects.filter(owner=user, acknowledged=False)
        if user.is_authenticated
        else []
    )
    has_toasts = len(toast_messages) > 0

    return {
        "has_toasts": has_toasts,
        "toast_messages": toast_messages,
    }


def app_version(request):
    return {"app_version": utils.app_version}