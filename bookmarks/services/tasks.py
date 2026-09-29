import contextlib
import functools
import logging

import waybackpy
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from huey.contrib.djhuey import HUEY as huey
from huey.exceptions import TaskLockedException
from waybackpy.exceptions import TooManyRequestsError, WaybackError

from bookmarks.models import Bookmark, BookmarkAsset, Tag, UserProfile, Webhook
from bookmarks.services import (
    assets,
    favicon_loader,
    http_client,
    preview_image_loader,
    webhooks,
)
from bookmarks.services.website_loader import DEFAULT_USER_AGENT, load_website_metadata

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
    with track_bookmark_changes(bookmark.owner, [bookmark.id]):
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
    user = User.objects.get(id=user_id)
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
    user = User.objects.get(id=user_id)
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
    user = User.objects.get(id=user_id)
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


def refresh_metadata(bookmark: Bookmark):
    if not settings.LD_DISABLE_BACKGROUND_TASKS:
        _refresh_metadata_task(bookmark.id)


@task()
def _refresh_metadata_task(bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return

    logger.info(f"Refresh metadata for bookmark. url={bookmark.url}")

    metadata = load_website_metadata(bookmark.url)
    with track_bookmark_changes(bookmark.owner, [bookmark.id]):
        if metadata.title:
            bookmark.title = metadata.title
        if metadata.description:
            bookmark.description = metadata.description
        bookmark.date_modified = timezone.now()
        # Only save the refreshed fields. The bookmark was loaded before
        # loading the metadata, saving all fields would revert changes that
        # were made in the meantime.
        bookmark.save(update_fields=["title", "description", "date_modified"])
    logger.info(f"Successfully refreshed metadata for bookmark. url={bookmark.url}")


def is_html_snapshot_feature_active() -> bool:
    return settings.LD_ENABLE_SNAPSHOTS and not settings.LD_DISABLE_BACKGROUND_TASKS


def create_html_snapshot(bookmark: Bookmark):
    if not is_html_snapshot_feature_active():
        return

    asset = assets.create_snapshot_asset(bookmark)
    asset.save()

    _trigger_html_snapshot_processing()


def create_html_snapshots(bookmark_list: list[Bookmark]):
    if not is_html_snapshot_feature_active():
        return

    assets_to_create = []
    for bookmark in bookmark_list:
        asset = assets.create_snapshot_asset(bookmark)
        assets_to_create.append(asset)

    BookmarkAsset.objects.bulk_create(assets_to_create)

    _trigger_html_snapshot_processing()


# single-file does not support running multiple instances in parallel, so we can
# not queue up a task per snapshot. Instead, a single task processes all pending
# assets in sequence, and is triggered whenever new assets are created. The lock
# ensures that only one of these tasks is running at a time.
_html_snapshot_lock = huey.lock_task("html-snapshots-lock")


def _trigger_html_snapshot_processing():
    # If a task is already running, it also picks up the assets that were just
    # created, either in its processing loop or when checking for remaining
    # assets after releasing the lock. Skip queuing a task that would only be
    # dropped by the lock anyway.
    if _html_snapshot_lock.is_locked():
        return

    _process_html_snapshots_task()


def _get_next_pending_asset() -> BookmarkAsset | None:
    return (
        BookmarkAsset.objects.filter(
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_PENDING,
        )
        .order_by("date_created", "id")
        .first()
    )


@task()
def _process_html_snapshots_task():
    # Tasks may still be queued after the feature has been disabled
    if not is_html_snapshot_feature_active():
        return

    try:
        with _html_snapshot_lock:
            # Processing an asset always moves it off the pending status, so
            # the loop terminates once all pending assets have been processed.
            while asset := _get_next_pending_asset():
                _create_html_snapshot(asset)
    except TaskLockedException:
        # Another task is already creating snapshots. As it processes assets
        # until there are no pending ones left, it also picks up the assets that
        # this task was triggered for.
        return

    # Assets that were created while holding the lock may have triggered a task
    # that was dropped above, in which case they have to be picked up here.
    if _get_next_pending_asset():
        _process_html_snapshots_task()


@huey.on_startup()
def _process_html_snapshots_on_startup():
    # Pick up assets that are still pending, for example because the consumer
    # was stopped while creating snapshots. This hook runs once per consumer
    # worker, the additional tasks are dropped by the lock.
    if is_html_snapshot_feature_active():
        _process_html_snapshots_task()


def _create_html_snapshot(asset: BookmarkAsset):
    logger.info(f"Create HTML snapshot for bookmark. url={asset.bookmark.url}")

    try:
        assets.create_snapshot(asset)

        logger.info(
            f"Successfully created HTML snapshot for bookmark. url={asset.bookmark.url}"
        )
    except Exception as error:
        logger.error(
            f"Failed to create HTML snapshot for bookmark. url={asset.bookmark.url}",
            exc_info=error,
        )


@task()
def _schedule_html_snapshots_task():
    # Snapshots are no longer created by a periodic task, keeping the task
    # function for now to prevent errors when huey tries to run the task
    pass


@task()
def _create_html_snapshot_task(asset_id: int):
    # Snapshots are now created by _process_html_snapshots_task, keeping the
    # task function for now to prevent errors when huey tries to run the task
    pass


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


def is_webhooks_feature_active() -> bool:
    return not settings.LD_DISABLE_BACKGROUND_TASKS


class BookmarkChanges:
    """
    Records the state of bookmarks before a change, and sends webhook events
    for everything that changed once the change is complete. Usually used
    through track_bookmark_changes. Must be used within a transaction that
    covers the whole change. Changes to the same bookmark must not be tracked by
    multiple instances at once, as that would send duplicate events.

    Failing to track changes never fails the change itself. Errors are logged,
    and no events are sent for the change.
    """

    def __init__(self, user: User):
        self.user = user
        # Skip tracking entirely if there is no webhook that could receive events
        self.enabled = (
            is_webhooks_feature_active()
            and Webhook.objects.filter(owner=user, enabled=True).exists()
        )
        # Bookmark data before the change by ID, None for created bookmarks
        self._before: dict[int, dict | None] = {}

    def track(self, bookmark_ids):
        """
        Records the current state of bookmarks that are about to change. Only
        bookmarks of the user are tracked. IDs can be passed as a lazy
        queryset, which is only evaluated if tracking is enabled.
        """
        if not self.enabled:
            return
        try:
            # Savepoint, so that errors leave the transaction usable
            with transaction.atomic():
                untracked_ids = [
                    bookmark_id
                    for bookmark_id in bookmark_ids
                    if bookmark_id not in self._before
                ]
                if not untracked_ids:
                    return
                # Lock the bookmarks until the transaction completes, so that
                # concurrent changes wait for this one, and are compared against
                # its result. SQLite does not support row locks, instead
                # transactions lock the whole database when they start.
                bookmarks = (
                    Bookmark.objects.filter(owner=self.user, id__in=untracked_ids)
                    .order_by("id")
                    .select_for_update()
                )
                for data in webhooks.serialize_bookmarks(bookmarks):
                    self._before[data["id"]] = data
        except Exception:
            self._disable("Failed to record the state of bookmarks")

    def lock_tags(self, tags):
        """
        Locks tags that are about to be added to bookmarks, so that renaming,
        merging or deleting the tags concurrently either completes before, or
        waits until this change is complete. Otherwise, events could contain
        outdated tag names. Must be called before tracking bookmarks, as tag
        changes lock tags before bookmarks, and locking in a different order
        could result in deadlocks.
        """
        if not self.enabled:
            return
        tag_ids = [tag.id for tag in tags]
        if not tag_ids:
            return
        try:
            with transaction.atomic():
                list(
                    Tag.objects.filter(id__in=tag_ids)
                    .order_by("id")
                    .select_for_update(no_key=True)
                )
        except Exception:
            self._disable("Failed to lock tags")

    def track_created(self, bookmark: Bookmark):
        """Records a bookmark that was created as part of the change."""
        if self.enabled:
            self._before.setdefault(bookmark.id, None)

    def send_events(self):
        """
        Compares the tracked bookmarks with their current state, and queues
        messages for the resulting events once the current transaction commits.
        """
        if not self.enabled or not self._before:
            return
        try:
            with transaction.atomic():
                bookmarks = Bookmark.objects.filter(
                    owner=self.user, id__in=self._before
                )
                after = {
                    data["id"]: data for data in webhooks.serialize_bookmarks(bookmarks)
                }

            changes = []
            for bookmark_id, before_data in self._before.items():
                after_data = after.get(bookmark_id)
                for event in webhooks.get_change_events(before_data, after_data):
                    # Deleted bookmarks are reported with their last known state
                    changes.append((event, after_data or before_data))
            # Determined while bookmarks are locked, so that the timestamps of
            # consecutive changes to a bookmark increase
            timestamp = timezone.now()
        except Exception:
            self._disable("Failed to determine changes of bookmarks")
            return
        finally:
            self._before = {}

        if changes:
            # Do not notify webhooks about changes that are rolled back. Create
            # messages after committing, to keep the transaction short.
            user = self.user
            transaction.on_commit(
                lambda: _queue_webhook_messages(user, changes, timestamp)
            )

    def _disable(self, message: str):
        logger.exception(
            f"{message}, webhook events are not sent for this change. user={self.user.username}"
        )
        self.enabled = False
        self._before = {}


def _queue_webhook_messages(user: User, changes: list[tuple[str, dict]], timestamp):
    # Runs after the change has been committed, errors must not fail the
    # request, or prevent queuing the remaining messages
    try:
        messages = webhooks.create_messages(user, changes, timestamp)
    except Exception:
        logger.exception(f"Failed to create webhook messages. user={user.username}")
        return

    for message in messages:
        try:
            _deliver_webhook_task(message.webhook_id, message.message_id, message.body)
        except Exception:
            logger.exception(
                f"Failed to queue webhook message. webhook_id={message.webhook_id} message_id={message.message_id}"
            )


@contextlib.contextmanager
def track_bookmark_changes(user: User, bookmark_ids=()):
    """
    Sends webhook events for changes made to bookmarks of the user within the
    block. Bookmarks that change must be passed up front, bookmarks created
    within the block must be registered with track_created on the yielded
    instance. If the user has webhooks, the block runs in a transaction, so
    that events are only sent once the change is persisted, and not at all if
    the change fails. Otherwise, the block runs as is.
    """
    changes = BookmarkChanges(user)
    if not changes.enabled:
        yield changes
        return

    with transaction.atomic():
        changes.track(bookmark_ids)
        yield changes
        changes.send_events()


@contextlib.contextmanager
def track_bookmark_changes_of_all_owners(bookmark_ids):
    """
    Like track_bookmark_changes, for bookmarks that can belong to different
    users, such as in the admin panel. Each owner's webhooks only receive
    events for their own bookmarks.
    """
    bookmark_ids = list(bookmark_ids)
    # Consistent order, so that concurrent operations lock bookmarks in the
    # same order
    owners = (
        User.objects.filter(bookmark__id__in=bookmark_ids).distinct().order_by("id")
    )
    with contextlib.ExitStack() as stack:
        for owner in owners:
            stack.enter_context(track_bookmark_changes(owner, bookmark_ids))
        yield


@task()
def _deliver_webhook_task(webhook_id: int, message_id: str, body: str):
    # The webhook may have been deleted or disabled while the message was queued
    webhook = Webhook.objects.filter(id=webhook_id).first()
    if not webhook or not webhook.enabled:
        return

    try:
        webhooks.deliver(webhook, message_id, body)
    except http_client.BlockedAddressError:
        # Retrying does not help, the request would be blocked again
        return
    except Exception as error:
        logger.warning(
            f"Failed to deliver webhook message. webhook={webhook.name} url={webhook.url} error={error}"
        )
        raise
