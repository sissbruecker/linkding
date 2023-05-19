import logging

import waybackpy
from background_task import background
from background_task.models import Task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from waybackpy.exceptions import WaybackError, TooManyRequestsError, NoCDXRecordFound

import bookmarks.services.wayback
from bookmarks.models import Bookmark, UserProfile
from bookmarks.services import favicon_loader
from bookmarks.services.website_loader import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)


def is_web_archive_integration_active(user: User) -> bool:
    background_tasks_enabled = not settings.LD_DISABLE_BACKGROUND_TASKS
    web_archive_integration_enabled = \
        user.profile.web_archive_integration == UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED

    return background_tasks_enabled and web_archive_integration_enabled


def create_web_archive_snapshot(user: User, bookmark: Bookmark, force_update: bool):
    if is_web_archive_integration_active(user):
        _create_web_archive_snapshot_task(bookmark.id, force_update)


def _load_newest_snapshot(bookmark: Bookmark):
    try:
        logger.info(f'Load existing snapshot for bookmark. url={bookmark.url}')
        cdx_api = bookmarks.services.wayback.CustomWaybackMachineCDXServerAPI(bookmark.url)
        existing_snapshot = cdx_api.newest()

        if existing_snapshot:
            bookmark.web_archive_snapshot_url = existing_snapshot.archive_url
            bookmark.save(update_fields=['web_archive_snapshot_url'])
            logger.info(f'Using newest snapshot. url={bookmark.url} from={existing_snapshot.datetime_timestamp}')

    except NoCDXRecordFound:
        logger.info(f'Could not find any snapshots for bookmark. url={bookmark.url}')
    except WaybackError as error:
        logger.error(f'Failed to load existing snapshot. url={bookmark.url}', exc_info=error)


def _create_snapshot(bookmark: Bookmark):
    logger.info(f'Create new snapshot for bookmark. url={bookmark.url}...')
    archive = waybackpy.WaybackMachineSaveAPI(bookmark.url, DEFAULT_USER_AGENT, max_tries=1)
    archive.save()
    bookmark.web_archive_snapshot_url = archive.archive_url
    bookmark.save(update_fields=['web_archive_snapshot_url'])
    logger.info(f'Successfully created new snapshot for bookmark:. url={bookmark.url}')


@background()
def _create_web_archive_snapshot_task(bookmark_id: int, force_update: bool):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return

    # Skip if snapshot exists and update is not explicitly requested
    if bookmark.web_archive_snapshot_url and not force_update:
        return

    # Create new snapshot
    try:
        _create_snapshot(bookmark)
        return
    except TooManyRequestsError:
        logger.error(
            f'Failed to create snapshot due to rate limiting, trying to load newest snapshot as fallback. url={bookmark.url}')
    except WaybackError as error:
        logger.error(f'Failed to create snapshot, trying to load newest snapshot as fallback. url={bookmark.url}',
                     exc_info=error)

    # Load the newest snapshot as fallback
    _load_newest_snapshot(bookmark)


@background()
def _load_web_archive_snapshot_task(bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return
    # Skip if snapshot exists
    if bookmark.web_archive_snapshot_url:
        return
    # Load the newest snapshot
    _load_newest_snapshot(bookmark)


def schedule_bookmarks_without_snapshots(user: User):
    if is_web_archive_integration_active(user):
        _schedule_bookmarks_without_snapshots_task(user.id)


@background()
def _schedule_bookmarks_without_snapshots_task(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks_without_snapshots = Bookmark.objects.filter(web_archive_snapshot_url__exact='', owner=user)

    for bookmark in bookmarks_without_snapshots:
        # To prevent rate limit errors from the Wayback API only try to load the latest snapshots instead of creating
        # new ones when processing bookmarks in bulk
        _load_web_archive_snapshot_task(bookmark.id)


def is_favicon_feature_active(user: User) -> bool:
    background_tasks_enabled = not settings.LD_DISABLE_BACKGROUND_TASKS

    return background_tasks_enabled and user.profile.enable_favicons


def load_favicon(user: User, bookmark: Bookmark):
    if is_favicon_feature_active(user):
        _load_favicon_task(bookmark.id)


@background()
def _load_favicon_task(bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return

    logger.info(f'Load favicon for bookmark. url={bookmark.url}')

    new_favicon = favicon_loader.load_favicon(bookmark.url)

    if new_favicon != bookmark.favicon_file:
        bookmark.favicon_file = new_favicon
        bookmark.save(update_fields=['favicon_file'])
        logger.info(f'Successfully updated favicon for bookmark. url={bookmark.url} icon={new_favicon}')


def schedule_bookmarks_without_favicons(user: User):
    if is_favicon_feature_active(user):
        _schedule_bookmarks_without_favicons_task(user.id)


@background()
def _schedule_bookmarks_without_favicons_task(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks = Bookmark.objects.filter(favicon_file__exact='', owner=user)
    tasks = []

    for bookmark in bookmarks:
        task = Task.objects.new_task(task_name='bookmarks.services.tasks._load_favicon_task', args=(bookmark.id,))
        tasks.append(task)

    Task.objects.bulk_create(tasks)


def schedule_refresh_favicons(user: User):
    if is_favicon_feature_active(user) and settings.LD_ENABLE_REFRESH_FAVICONS:
        _schedule_refresh_favicons_task(user.id)


@background()
def _schedule_refresh_favicons_task(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks = Bookmark.objects.filter(owner=user)
    tasks = []

    for bookmark in bookmarks:
        task = Task.objects.new_task(task_name='bookmarks.services.tasks._load_favicon_task', args=(bookmark.id,))
        tasks.append(task)

    Task.objects.bulk_create(tasks)
