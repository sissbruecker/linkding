import functools
import logging
import os
from typing import List

import waybackpy
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone, formats
from huey import crontab
from huey.contrib.djhuey import HUEY as huey
from huey.exceptions import TaskLockedException
from waybackpy.exceptions import WaybackError, TooManyRequestsError

from bookmarks.models import Bookmark, BookmarkAsset, UserProfile
from bookmarks.services import favicon_loader, singlefile, preview_image_loader
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
            f"Failed to create snapshot due to rate limiting. url={bookmark.url}"
        )
    except WaybackError as error:
        logger.error(
            f"Failed to create snapshot. url={bookmark.url}",
            exc_info=error,
        )


@task()
def _load_web_archive_snapshot_task(bookmark_id: int):
    # Loading snapshots from CDX API has been removed, keeping the task function
    # for now to prevent errors when huey tries to run the task
    pass


@task()
def _schedule_bookmarks_without_snapshots_task(user_id: int):
    # Loading snapshots from CDX API has been removed, keeping the task function
    # for now to prevent errors when huey tries to run the task
    pass


def is_favicon_feature_active(user: User) -> bool:
    background_tasks_enabled = not settings.LD_DISABLE_BACKGROUND_TASKS

    return background_tasks_enabled and user.profile.enable_favicons


def is_preview_feature_active(user: User) -> bool:
    return (
        user.profile.enable_preview_images and not settings.LD_DISABLE_BACKGROUND_TASKS
    )


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


def load_preview_image(user: User, bookmark: Bookmark):
    if is_preview_feature_active(user):
        _load_preview_image_task(bookmark.id)


@task()
def _load_preview_image_task(bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return

    logger.info(f"Load preview image for bookmark. url={bookmark.url}")

    new_preview_image_file = preview_image_loader.load_preview_image(bookmark.url)

    if new_preview_image_file != bookmark.preview_image_file:
        bookmark.preview_image_file = new_preview_image_file or ""
        bookmark.save(update_fields=["preview_image_file"])
        logger.info(
            f"Successfully updated preview image for bookmark. url={bookmark.url} preview_image_file={new_preview_image_file}"
        )


def schedule_bookmarks_without_previews(user: User):
    if is_preview_feature_active(user):
        _schedule_bookmarks_without_previews_task(user.id)


@task()
def _schedule_bookmarks_without_previews_task(user_id: int):
    user = get_user_model().objects.get(id=user_id)
    bookmarks = Bookmark.objects.filter(
        Q(preview_image_file__exact=""),
        owner=user,
    )

    # TODO: Implement bulk task creation
    for bookmark in bookmarks:
        try:
            _load_preview_image_task(bookmark.id)
        except Exception as exc:
            logging.exception(exc)


def is_html_snapshot_feature_active() -> bool:
    return settings.LD_ENABLE_SNAPSHOTS and not settings.LD_DISABLE_BACKGROUND_TASKS


def create_html_snapshot(bookmark: Bookmark):
    if not is_html_snapshot_feature_active():
        return

    asset = _create_snapshot_asset(bookmark)
    asset.save()


def create_html_snapshots(bookmark_list: List[Bookmark]):
    if not is_html_snapshot_feature_active():
        return

    assets_to_create = []
    for bookmark in bookmark_list:
        asset = _create_snapshot_asset(bookmark)
        assets_to_create.append(asset)

    BookmarkAsset.objects.bulk_create(assets_to_create)


MAX_SNAPSHOT_FILENAME_LENGTH = 192


def _create_snapshot_asset(bookmark: Bookmark) -> BookmarkAsset:
    timestamp = formats.date_format(timezone.now(), "SHORT_DATE_FORMAT")
    asset = BookmarkAsset(
        bookmark=bookmark,
        asset_type=BookmarkAsset.TYPE_SNAPSHOT,
        content_type="text/html",
        display_name=f"HTML snapshot from {timestamp}",
        status=BookmarkAsset.STATUS_PENDING,
    )
    return asset


def _generate_snapshot_filename(asset: BookmarkAsset) -> str:
    def sanitize_char(char):
        if char.isalnum() or char in ("-", "_", "."):
            return char
        else:
            return "_"

    formatted_datetime = asset.date_created.strftime("%Y-%m-%d_%H%M%S")
    sanitized_url = "".join(sanitize_char(char) for char in asset.bookmark.url)

    # Calculate the length of the non-URL parts of the filename
    non_url_length = len(f"{asset.asset_type}{formatted_datetime}__.html.gz")
    # Calculate the maximum length for the URL part
    max_url_length = MAX_SNAPSHOT_FILENAME_LENGTH - non_url_length
    # Truncate the URL if necessary
    sanitized_url = sanitized_url[:max_url_length]

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


def create_missing_html_snapshots(user: User) -> int:
    if not is_html_snapshot_feature_active():
        return 0

    bookmarks_without_snapshots = Bookmark.objects.filter(owner=user).exclude(
        bookmarkasset__asset_type=BookmarkAsset.TYPE_SNAPSHOT,
        bookmarkasset__status__in=[
            BookmarkAsset.STATUS_PENDING,
            BookmarkAsset.STATUS_COMPLETE,
        ],
    )
    bookmarks_without_snapshots |= Bookmark.objects.filter(owner=user).exclude(
        bookmarkasset__asset_type=BookmarkAsset.TYPE_SNAPSHOT
    )

    create_html_snapshots(list(bookmarks_without_snapshots))

    return bookmarks_without_snapshots.count()
