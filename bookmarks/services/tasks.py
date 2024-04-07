import functools
import logging
import os

import waybackpy
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.utils import timezone, formats
from huey import crontab
from huey.contrib.djhuey import HUEY as huey
from huey.exceptions import TaskLockedException
from waybackpy.exceptions import WaybackError, TooManyRequestsError, NoCDXRecordFound

import bookmarks.services.wayback
from bookmarks.models import Bookmark, BookmarkAsset, UserProfile
from bookmarks.services import favicon_loader, singlefile
from bookmarks.services.website_loader import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)


# Create custom decorator for Huey tasks that implements exponential backoff
# Taken from: https://huey.readthedocs.io/en/latest/guide.html#tips-and-tricks
# Retry 1: 60
# Retry 2: 240
# Retry 3: 960
# Retry 4: 3840
# Retry 5: 15360
def task(retries=5, retry_delay=15, retry_backoff=4):
    def deco(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            task = kwargs.pop("task")
            try:
                return fn(*args, **kwargs)
            except TaskLockedException as exc:
                # Task locks are currently only used as workaround to enforce
                # running specific types of tasks (e.g. singlefile snapshots)
                # sequentially. In that case don't reduce the number of retries.
                task.retries = retries
                raise exc
            except Exception as exc:
                task.retry_delay *= retry_backoff
                raise exc

        return huey.task(retries=retries, retry_delay=retry_delay, context=True)(inner)

    return deco


def is_web_archive_integration_active(user: User) -> bool:
    background_tasks_enabled = not settings.LD_DISABLE_BACKGROUND_TASKS
    web_archive_integration_enabled = (
        user.profile.web_archive_integration
        == UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED
    )

    return background_tasks_enabled and web_archive_integration_enabled


def create_web_archive_snapshot(user: User, bookmark: Bookmark, force_update: bool):
    if is_web_archive_integration_active(user):
        _create_web_archive_snapshot_task(bookmark.id, force_update)


def _load_newest_snapshot(bookmark: Bookmark):
    try:
        logger.info(f"Load existing snapshot for bookmark. url={bookmark.url}")
        cdx_api = bookmarks.services.wayback.CustomWaybackMachineCDXServerAPI(
            bookmark.url
        )
        existing_snapshot = cdx_api.newest()

        if existing_snapshot:
            bookmark.web_archive_snapshot_url = existing_snapshot.archive_url
            bookmark.save(update_fields=["web_archive_snapshot_url"])
            logger.info(
                f"Using newest snapshot. url={bookmark.url} from={existing_snapshot.datetime_timestamp}"
            )

    except NoCDXRecordFound:
        logger.info(f"Could not find any snapshots for bookmark. url={bookmark.url}")
    except WaybackError as error:
        logger.error(
            f"Failed to load existing snapshot. url={bookmark.url}", exc_info=error
        )


def _create_snapshot(bookmark: Bookmark):
    logger.info(f"Create new snapshot for bookmark. url={bookmark.url}...")
    archive = waybackpy.WaybackMachineSaveAPI(
        bookmark.url, DEFAULT_USER_AGENT, max_tries=1
    )
    archive.save()
    bookmark.web_archive_snapshot_url = archive.archive_url
    bookmark.save(update_fields=["web_archive_snapshot_url"])
    logger.info(f"Successfully created new snapshot for bookmark:. url={bookmark.url}")


@task()
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
            f"Failed to create snapshot due to rate limiting, trying to load newest snapshot as fallback. url={bookmark.url}"
        )
    except WaybackError as error:
        logger.error(
            f"Failed to create snapshot, trying to load newest snapshot as fallback. url={bookmark.url}",
            exc_info=error,
        )

    # Load the newest snapshot as fallback
    _load_newest_snapshot(bookmark)


@task()
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


@task()
def _schedule_bookmarks_without_snapshots_task(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks_without_snapshots = Bookmark.objects.filter(
        web_archive_snapshot_url__exact="", owner=user
    )

    # TODO: Implement bulk task creation
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


@task()
def _load_favicon_task(bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return

    logger.info(f"Load favicon for bookmark. url={bookmark.url}")

    new_favicon_file = favicon_loader.load_favicon(bookmark.url)

    if new_favicon_file != bookmark.favicon_file:
        bookmark.favicon_file = new_favicon_file
        bookmark.save(update_fields=["favicon_file"])
        logger.info(
            f"Successfully updated favicon for bookmark. url={bookmark.url} icon={new_favicon_file}"
        )


def schedule_bookmarks_without_favicons(user: User):
    if is_favicon_feature_active(user):
        _schedule_bookmarks_without_favicons_task(user.id)


@task()
def _schedule_bookmarks_without_favicons_task(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks = Bookmark.objects.filter(favicon_file__exact="", owner=user)

    # TODO: Implement bulk task creation
    for bookmark in bookmarks:
        _load_favicon_task(bookmark.id)
        pass


def schedule_refresh_favicons(user: User):
    if is_favicon_feature_active(user) and settings.LD_ENABLE_REFRESH_FAVICONS:
        _schedule_refresh_favicons_task(user.id)


@task()
def _schedule_refresh_favicons_task(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks = Bookmark.objects.filter(owner=user)

    # TODO: Implement bulk task creation
    for bookmark in bookmarks:
        _load_favicon_task(bookmark.id)


def is_html_snapshot_feature_active() -> bool:
    return settings.LD_ENABLE_SNAPSHOTS and not settings.LD_DISABLE_BACKGROUND_TASKS


def create_html_snapshot(bookmark: Bookmark):
    if not is_html_snapshot_feature_active():
        return

    timestamp = formats.date_format(timezone.now(), "SHORT_DATE_FORMAT")
    asset = BookmarkAsset(
        bookmark=bookmark,
        asset_type=BookmarkAsset.TYPE_SNAPSHOT,
        content_type="text/html",
        display_name=f"HTML snapshot from {timestamp}",
        status=BookmarkAsset.STATUS_PENDING,
    )
    asset.save()


def _generate_snapshot_filename(asset: BookmarkAsset) -> str:
    def sanitize_char(char):
        if char.isalnum() or char in ("-", "_", "."):
            return char
        else:
            return "_"

    formatted_datetime = asset.date_created.strftime("%Y-%m-%d_%H%M%S")
    sanitized_url = "".join(sanitize_char(char) for char in asset.bookmark.url)

    return f"{asset.asset_type}_{formatted_datetime}_{sanitized_url}.html.gz"


# singe-file does not support running multiple instances in parallel, so we can
# not queue up multiple snapshot tasks at once. Instead, schedule a periodic
# task that grabs a number of pending assets and creates snapshots for them in
# sequence. The task uses a lock to ensure that a new task isn't scheduled
# before the previous one has finished.
@huey.periodic_task(crontab(minute="*"))
@huey.lock_task("schedule-html-snapshots-lock")
def _schedule_html_snapshots_task():
    # Get five pending assets
    assets = BookmarkAsset.objects.filter(status=BookmarkAsset.STATUS_PENDING).order_by(
        "date_created"
    )[:5]

    for asset in assets:
        _create_html_snapshot_task(asset.id)


def _create_html_snapshot_task(asset_id: int):
    try:
        asset = BookmarkAsset.objects.get(id=asset_id)
    except BookmarkAsset.DoesNotExist:
        return

    logger.info(f"Create HTML snapshot for bookmark. url={asset.bookmark.url}")

    try:
        filename = _generate_snapshot_filename(asset)
        filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
        singlefile.create_snapshot(asset.bookmark.url, filepath)
        asset.status = BookmarkAsset.STATUS_COMPLETE
        asset.file = filename
        asset.gzip = True
        asset.save()
        logger.info(
            f"Successfully created HTML snapshot for bookmark. url={asset.bookmark.url}"
        )
    except Exception as error:
        logger.error(
            f"Failed to HTML snapshot for bookmark. url={asset.bookmark.url}",
            exc_info=error,
        )
        asset.status = BookmarkAsset.STATUS_FAILURE
        asset.save()
