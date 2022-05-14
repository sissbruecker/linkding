from bookmarks.models import Toast


def toasts(request):
    user = request.user if hasattr(request, 'user') else None
    toast_messages = Toast.objects.filter(owner=user, acknowledged=False) if user and user.is_authenticated else []
    has_toasts = len(toast_messages) > 0

    return {
        'has_toasts': has_toasts,
        'toast_messages': toast_messages,
    }
