from bookmarks import queries
from bookmarks.models import BookmarkSearch, Toast
from bookmarks import utils


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


def public_shares(request):
    # Only check for public shares for anonymous users
    if not request.user.is_authenticated:
        query_set = queries.query_shared_bookmarks(
            None, request.user_profile, BookmarkSearch(), True
        )
        has_public_shares = query_set.count() > 0
        return {
            "has_public_shares": has_public_shares,
        }

    return {}


def app_version(request):
    return {"app_version": utils.app_version}
