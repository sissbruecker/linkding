"""
Tests webhook events for concurrent bookmark changes. These tests run
operations in separate threads, each with its own database connection. With
SQLite, production uses a database file in WAL mode, where concurrent
connections interact differently than with the in-memory test database, so the
threads connect to a copy of the test database that is stored in a file in WAL
mode. With PostgreSQL, the threads connect to the test database directly.
"""

import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from unittest import mock

from django.db import connections
from django.test import TransactionTestCase

from bookmarks.models import Bookmark, Tag, Webhook
from bookmarks.services import bookmarks as bookmark_service
from bookmarks.services import tags as tag_service
from bookmarks.services import tasks, webhooks
from bookmarks.tests.test_webhooks_tasks import WebhookTestMixin

# How long the first operation waits for the second one to reach a lock held
# by the first one
PAUSE = 0.5


class ConcurrentOperationsTestMixin(WebhookTestMixin):
    def setUp(self):
        super().setUp()
        self.db_settings = None

    def copy_database(self):
        """
        With SQLite, copies the test database into a file in WAL mode. Must be
        called after setting up test data, changes to the test database are not
        visible to the operations afterward.
        """
        source = connections["default"]
        if source.vendor != "sqlite":
            return
        self.db_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.db_dir, ignore_errors=True)
        source.ensure_connection()
        path = os.path.join(self.db_dir, "db.sqlite3")
        target = sqlite3.connect(path)
        source.connection.backup(target)
        target.execute("PRAGMA journal_mode=wal")
        target.close()
        self.db_settings = {**source.settings_dict, "NAME": path}

    def run_concurrently(self, first, second):
        """
        Runs two operations in separate threads. The first operation pauses
        after it recorded the state of the bookmarks it changes, or, if it does
        not track changes, after checking for webhooks. It resumes once the
        second operation has started, and, with PostgreSQL, is waiting for a
        lock held by the first operation. Verifies that the operations actually
        overlapped, and returns the exceptions raised by each.
        """
        first_paused = threading.Event()
        second_started = threading.Event()
        original_init = tasks.BookmarkChanges.__init__
        original_track = tasks.BookmarkChanges.track
        errors = {}
        times = {}

        def pause():
            if threading.current_thread().name == "first" and not first_paused.is_set():
                first_paused.set()
                self.assertTrue(
                    second_started.wait(timeout=5), "Second operation did not start"
                )
                self.wait_until_blocked()

        def init(changes, user):
            original_init(changes, user)
            if not changes.enabled:
                pause()

        def track(changes, bookmark_ids):
            original_track(changes, bookmark_ids)
            if changes._before:
                pause()

        def run(name, operation, wait_for=None):
            connection = self.connect()
            try:
                if wait_for:
                    self.assertTrue(
                        wait_for.wait(timeout=5), "First operation did not pause"
                    )
                    times["second_started"] = time.monotonic()
                    second_started.set()
                operation()
            except Exception as error:
                errors[name] = error
            finally:
                times[f"{name}_finished"] = time.monotonic()
                connection.close()

        with (
            mock.patch.object(tasks.BookmarkChanges, "__init__", init),
            mock.patch.object(tasks.BookmarkChanges, "track", track),
        ):
            threads = [
                threading.Thread(name="first", target=run, args=("first", first)),
                threading.Thread(
                    name="second", target=run, args=("second", second, first_paused)
                ),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

        # The second operation must have started while the first one was in
        # progress, otherwise the test did not exercise concurrent changes
        self.assertLess(times["second_started"], times["first_finished"])
        return errors

    def wait_until_blocked(self):
        """
        Waits until another connection waits for a lock. SQLite does not expose
        waiting connections, so it waits for a fixed time instead, in which the
        second operation reaches the lock held by the first one.
        """
        deadline = time.monotonic() + PAUSE
        connection = connections["default"]
        while time.monotonic() < deadline:
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                    )
                    if cursor.fetchone()[0] > 0:
                        return
            time.sleep(0.01)

    def connect(self):
        """Sets up the database connection of the current thread."""
        if self.db_settings:
            connections["default"] = connections["default"].__class__(
                self.db_settings, "default"
            )
        return connections["default"]

    def read(self, query):
        """Runs a query in a separate connection."""
        result = {}

        def run():
            connection = self.connect()
            try:
                result["value"] = query()
            finally:
                connection.close()

        thread = threading.Thread(target=run)
        thread.start()
        thread.join()
        return result["value"]

    def get_messages(self) -> list[dict]:
        return [
            json.loads(call.kwargs["data"]) for call in self.mock_post.call_args_list
        ]

    def assertLatestMessagesMatchCurrentState(self, bookmark_ids):
        """
        A receiver that applies messages ordered by their timestamp must end up
        with the current state of each bookmark.
        """
        latest = {}
        for message in sorted(self.get_messages(), key=lambda m: m["timestamp"]):
            latest[message["data"]["id"]] = message["data"]

        current = self.read(
            lambda: {
                data["id"]: data
                for data in webhooks.serialize_bookmarks(
                    Bookmark.objects.filter(id__in=bookmark_ids)
                )
            }
        )

        # The modification date alone does not count as a change, so it can be
        # newer than in the latest message
        def without_modification_date(data):
            return {k: v for k, v in (data or {}).items() if k != "date_modified"}

        for bookmark_id in bookmark_ids:
            self.assertEqual(
                without_modification_date(current[bookmark_id]),
                without_modification_date(latest.get(bookmark_id)),
            )


class WebhookConcurrencyTestCase(ConcurrentOperationsTestMixin, TransactionTestCase):
    def test_concurrent_write_does_not_fail_tracked_change(self):
        # Background tasks, such as loading favicons, write to bookmarks while
        # users change them
        bookmark = self.setup_bookmark()
        self.copy_database()

        errors = self.run_concurrently(
            lambda: bookmark_service.archive_bookmark(
                Bookmark.objects.get(id=bookmark.id)
            ),
            lambda: Bookmark.objects.filter(id=bookmark.id).update(
                favicon_file="favicon.png"
            ),
        )

        self.assertEqual({}, errors)
        stored = self.read(lambda: Bookmark.objects.get(id=bookmark.id))
        self.assertTrue(stored.is_archived)
        self.assertEqual("favicon.png", stored.favicon_file)
        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id)], self.get_sent_events()
        )

    def test_concurrent_write_does_not_fail_change_without_webhooks(self):
        # Users without webhooks must not be affected by change tracking
        self.webhook.delete()
        bookmark = self.setup_bookmark()
        self.copy_database()

        errors = self.run_concurrently(
            lambda: bookmark_service.archive_bookmark(
                Bookmark.objects.get(id=bookmark.id)
            ),
            lambda: Bookmark.objects.filter(id=bookmark.id).update(
                favicon_file="favicon.png"
            ),
        )

        self.assertEqual({}, errors)
        self.assertTrue(
            self.read(lambda: Bookmark.objects.get(id=bookmark.id).is_archived)
        )

    def test_concurrent_identical_changes_are_reported_once(self):
        bookmark = self.setup_bookmark()
        self.copy_database()

        def archive():
            bookmark_service.archive_bookmark(Bookmark.objects.get(id=bookmark.id))

        errors = self.run_concurrently(archive, archive)

        self.assertEqual({}, errors)
        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id)], self.get_sent_events()
        )

    def test_concurrent_different_changes_are_reported_in_order(self):
        bookmark = self.setup_bookmark()
        self.copy_database()

        errors = self.run_concurrently(
            lambda: bookmark_service.archive_bookmark(
                Bookmark.objects.get(id=bookmark.id)
            ),
            lambda: bookmark_service.mark_bookmarks_as_unread([bookmark.id], self.user),
        )

        self.assertEqual({}, errors)
        self.assertEqual(
            [
                (Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id),
                (Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id),
            ],
            self.get_sent_events(),
        )
        first, second = self.get_messages()
        self.assertLess(first["timestamp"], second["timestamp"])
        # The second change is reported based on the state after the first one
        self.assertTrue(second["data"]["is_archived"])
        self.assertLatestMessagesMatchCurrentState([bookmark.id])

    def rename_tag(self, tag_id: int, name: str):
        tag = Tag.objects.get(id=tag_id)
        with tag_service.track_tag_changes([tag]):
            tag.name = name
            tag.save()

    def test_concurrent_edit_does_not_revert_other_change(self):
        # The edit loads the bookmark before the archive is committed, and only
        # changes the title. It must neither revert the archive, nor report it.
        bookmark = self.setup_bookmark(title="Title")
        self.copy_database()

        def edit():
            stale = Bookmark.objects.get(id=bookmark.id)
            stale.title = "Edited"
            bookmark_service.update_bookmark(
                stale, None, self.user, update_fields=["title"]
            )

        errors = self.run_concurrently(
            lambda: bookmark_service.archive_bookmark(
                Bookmark.objects.get(id=bookmark.id)
            ),
            edit,
        )

        self.assertEqual({}, errors)
        stored = self.read(lambda: Bookmark.objects.get(id=bookmark.id))
        self.assertTrue(stored.is_archived)
        self.assertEqual("Edited", stored.title)
        self.assertEqual(
            [
                (Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id),
                (Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id),
            ],
            self.get_sent_events(),
        )
        self.assertLatestMessagesMatchCurrentState([bookmark.id])

    def test_concurrent_tag_rename_and_tagging(self):
        tag = self.setup_tag(name="tag1")
        tagged = self.setup_bookmark(tags=[tag])
        untagged = self.setup_bookmark()
        self.copy_database()

        errors = self.run_concurrently(
            lambda: self.rename_tag(tag.id, "renamed"),
            lambda: bookmark_service.tag_bookmarks(
                [untagged.id, tagged.id], "tag1", self.user
            ),
        )

        self.assertEqual({}, errors)
        self.assertLatestMessagesMatchCurrentState([tagged.id, untagged.id])

    def test_concurrent_tagging_and_tag_rename(self):
        # Tagging a bookmark that already has the tag, and one that does not,
        # while the tag is renamed. Both operations lock the tag and the
        # bookmarks, which must not deadlock.
        tag = self.setup_tag(name="tag1")
        tagged = self.setup_bookmark(tags=[tag])
        untagged = self.setup_bookmark()
        self.copy_database()

        errors = self.run_concurrently(
            lambda: bookmark_service.tag_bookmarks(
                [untagged.id, tagged.id], "tag1", self.user
            ),
            lambda: self.rename_tag(tag.id, "renamed"),
        )

        self.assertEqual({}, errors)
        self.assertEqual(
            ["renamed"],
            self.read(lambda: Bookmark.objects.get(id=untagged.id).tag_names),
        )
        self.assertLatestMessagesMatchCurrentState([tagged.id, untagged.id])

    def test_concurrent_edit_and_tag_rename(self):
        tag = self.setup_tag(name="tag1")
        tagged = self.setup_bookmark(tags=[tag])
        edited = self.setup_bookmark()
        self.copy_database()

        def edit():
            bookmark = Bookmark.objects.get(id=edited.id)
            bookmark.title = "Edited"
            bookmark_service.update_bookmark(bookmark, "tag1", self.user)

        errors = self.run_concurrently(edit, lambda: self.rename_tag(tag.id, "renamed"))

        self.assertEqual({}, errors)
        self.assertLatestMessagesMatchCurrentState([tagged.id, edited.id])

    def test_concurrent_tag_merge_and_tagging(self):
        target = self.setup_tag(name="target")
        merged = self.setup_tag(name="merged")
        with_merged = self.setup_bookmark(tags=[merged])
        untagged = self.setup_bookmark()
        self.copy_database()

        def merge():
            tags = list(Tag.objects.filter(id__in=[target.id, merged.id]))
            with tag_service.track_tag_changes(tags):
                target_tag = Tag.objects.get(id=target.id)
                through = Bookmark.tags.through
                through.objects.bulk_create(
                    [through(bookmark_id=with_merged.id, tag=target_tag)]
                )
                Tag.objects.filter(id=merged.id).delete()
                target_tag.name = "merged-target"
                target_tag.save()

        errors = self.run_concurrently(
            merge,
            lambda: bookmark_service.tag_bookmarks([untagged.id], "target", self.user),
        )

        self.assertEqual({}, errors)
        self.assertLatestMessagesMatchCurrentState([with_merged.id, untagged.id])
