import logging

import waybackpy
from background_task import background
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from waybackpy.exceptions import WaybackError

from bookmarks.models import Bookmark, UserProfile

logger = logging.getLogger(__name__)


def is_web_archive_integration_active(user: User) -> bool:
    background_tasks_enabled = not settings.LD_DISABLE_BACKGROUND_TASKS
    web_archive_integration_enabled = \
        user.profile.web_archive_integration == UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED

    return background_tasks_enabled and web_archive_integration_enabled


def create_web_archive_snapshot(user: User, bookmark: Bookmark, force_update: bool):
    if is_web_archive_integration_active(user):
        _create_web_archive_snapshot_task(bookmark.id, force_update)


@background()
def _create_web_archive_snapshot_task(bookmark_id: int, force_update: bool):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return

    # Skip if snapshot exists and update is not explicitly requested
    if bookmark.web_archive_snapshot_url and not force_update:
        return

    logger.debug(f'Create web archive link for bookmark: {bookmark}...')

    archive = waybackpy.WaybackMachineSaveAPI(bookmark.url, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36")

    try:
        archive.save()
    except WaybackError as error:
        logger.exception(f'Error creating web archive link for bookmark: {bookmark}...', exc_info=error)
        raise

    bookmark.web_archive_snapshot_url = archive.archive_url
    bookmark.save()
    logger.debug(f'Successfully created web archive link for bookmark: {bookmark}...')


def schedule_bookmarks_without_snapshots(user: User):
    if is_web_archive_integration_active(user):
        _schedule_bookmarks_without_snapshots_task(user.id)


@background()
def _schedule_bookmarks_without_snapshots_task(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks_without_snapshots = Bookmark.objects.filter(web_archive_snapshot_url__exact='', owner=user)

    for bookmark in bookmarks_without_snapshots:
        _create_web_archive_snapshot_task(bookmark.id, False)
