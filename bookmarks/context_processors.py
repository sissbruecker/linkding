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


def app_version(request):
    return {"app_version": utils.app_version}
