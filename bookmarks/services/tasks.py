import logging

import waybackpy
from background_task import background
from django.conf import settings
from django.contrib.auth import get_user_model
from waybackpy.exceptions import WaybackError

from bookmarks.models import Bookmark

logger = logging.getLogger(__name__)


def when_background_tasks_enabled(fn):
    def wrapper(*args, **kwargs):
        if settings.LD_DISABLE_BACKGROUND_TASKS:
            return
        return fn(*args, **kwargs)

    # Expose attributes from wrapped TaskProxy function
    attrs = vars(fn)
    for key, value in attrs.items():
        setattr(wrapper, key, value)

    return wrapper


@when_background_tasks_enabled
@background()
def create_web_archive_snapshot(bookmark_id: int, force_update: bool):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return

    # Skip if snapshot exists and update is not explicitly requested
    if bookmark.web_archive_snapshot_url and not force_update:
        return

    logger.debug(f'Create web archive link for bookmark: {bookmark}...')

    wayback = waybackpy.Url(bookmark.url)

    try:
        archive = wayback.save()
    except WaybackError as error:
        logger.exception(f'Error creating web archive link for bookmark: {bookmark}...', exc_info=error)
        raise

    bookmark.web_archive_snapshot_url = archive.archive_url
    bookmark.save()
    logger.debug(f'Successfully created web archive link for bookmark: {bookmark}...')


@when_background_tasks_enabled
@background()
def schedule_bookmarks_without_snapshots(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks_without_snapshots = Bookmark.objects.filter(web_archive_snapshot_url__exact='', owner=user)

    for bookmark in bookmarks_without_snapshots:
        create_web_archive_snapshot(bookmark.id, False)
