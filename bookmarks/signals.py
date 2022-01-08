from django.contrib.auth import user_logged_in
from django.dispatch import receiver
from bookmarks.services import tasks


@receiver(user_logged_in)
def user_logged_in(sender, request, user, **kwargs):
    tasks.schedule_bookmarks_without_snapshots(user)
