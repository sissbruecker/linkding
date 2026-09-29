"""
Tests for the guarantees that the webhook documentation makes: failures in
tracking changes never fail bookmark operations, messages from one operation
are consistent with each other, timestamps order messages for a bookmark, and
background tasks do not produce misleading events.
"""

import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from huey.contrib.djhuey import HUEY as huey
from rest_framework.test import APIClient

from bookmarks.api.routes import BookmarkViewSet
from bookmarks.models import ApiToken, Bookmark, Webhook
from bookmarks.services import assets, importer, tasks, webhooks, website_loader
from bookmarks.services import bookmarks as bookmark_service
from bookmarks.services import tags as tag_service
from bookmarks.tests.helpers import BookmarkHtmlTag, ImportTestMixin
from bookmarks.tests.test_webhooks_tasks import WebhookTestMixin
from bookmarks.views import access

UPDATED = Webhook.EVENT_BOOKMARK_UPDATED
ARCHIVED = Webhook.EVENT_BOOKMARK_ARCHIVED


class WebhookTrackingFailureTestCase(WebhookTestMixin, TestCase):
    def test_failure_to_record_state_does_not_fail_operation(self):
        bookmark = self.setup_bookmark()

        with (
            mock.patch.object(
                webhooks, "serialize_bookmarks", side_effect=Exception("Failed")
            ),
            self.assertLogs("bookmarks.services.tasks", "ERROR") as logs,
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.archive_bookmark(bookmark)

        bookmark.refresh_from_db()
        self.assertTrue(bookmark.is_archived)
        self.mock_post.assert_not_called()
        self.assertIn("Failed to record the state of bookmarks", logs.output[0])

    def test_failure_to_determine_changes_does_not_fail_operation(self):
        bookmark = self.setup_bookmark()

        with (
            mock.patch.object(
                webhooks, "get_change_events", side_effect=Exception("Failed")
            ),
            self.assertLogs("bookmarks.services.tasks", "ERROR") as logs,
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.archive_bookmark(bookmark)

        bookmark.refresh_from_db()
        self.assertTrue(bookmark.is_archived)
        self.mock_post.assert_not_called()
        self.assertIn("Failed to determine changes of bookmarks", logs.output[0])

    def test_failure_to_create_messages_does_not_fail_operation(self):
        bookmark = self.setup_bookmark()

        with (
            mock.patch.object(
                webhooks, "create_messages", side_effect=Exception("Failed")
            ),
            self.assertLogs("bookmarks.services.tasks", "ERROR") as logs,
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.archive_bookmark(bookmark)

        bookmark.refresh_from_db()
        self.assertTrue(bookmark.is_archived)
        self.mock_post.assert_not_called()
        self.assertIn("Failed to create webhook messages", logs.output[0])

    def test_failure_to_queue_message_does_not_affect_other_messages(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        original_task = tasks._deliver_webhook_task
        calls = []

        def deliver(webhook_id, message_id, body):
            calls.append(message_id)
            if len(calls) == 1:
                raise Exception("Queue unavailable")
            return original_task(webhook_id, message_id, body)

        with (
            mock.patch.object(tasks, "_deliver_webhook_task", side_effect=deliver),
            self.assertLogs("bookmarks.services.tasks", "ERROR") as logs,
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.archive_bookmarks([bookmark1.id, bookmark2.id], self.user)

        self.assertEqual(2, len(calls))
        self.assertEqual(1, len(self.get_sent_events()))
        self.assertIn("Failed to queue webhook message", logs.output[0])

    def test_recording_delivery_failure_does_not_retry_successful_delivery(self):
        # A retry would deliver the message a second time
        with (
            mock.patch.object(
                Webhook.objects, "filter", side_effect=Exception("Locked")
            ) as mock_filter,
            self.assertLogs("bookmarks.services.webhooks", "ERROR"),
        ):
            webhooks.deliver(self.webhook, "msg_123", "{}")

        mock_filter.assert_called_once()
        self.mock_post.assert_called_once()
        self.assertEqual(0, huey.scheduled_count())


class WebhookTransactionTestCase(WebhookTestMixin, TestCase):
    def test_rolled_back_savepoint_within_change(self):
        # Only the committed part of a change is reported
        bookmark = self.setup_bookmark(title="Initial")

        with (
            self.captureOnCommitCallbacks(execute=True),
            tasks.track_bookmark_changes(self.user, [bookmark.id]),
        ):
            bookmark.title = "Committed"
            bookmark.save()
            try:
                with transaction.atomic():
                    Bookmark.objects.filter(id=bookmark.id).update(
                        title="Rolled back", is_archived=True
                    )
                    raise IntegrityError()
            except IntegrityError:
                pass

        self.assertEqual([(UPDATED, bookmark.id)], self.get_sent_events())
        data = self.get_sent_bodies()[0]["data"]
        self.assertEqual("Committed", data["title"])
        self.assertFalse(data["is_archived"])

    def test_locks_tracked_bookmarks_in_consistent_order(self):
        # SQLite ignores row locks, verify that databases that support them
        # lock bookmarks when recording their state
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        querysets = []
        original_serialize = webhooks.serialize_bookmarks

        def serialize(queryset):
            querysets.append(queryset)
            return original_serialize(queryset)

        with (
            mock.patch.object(webhooks, "serialize_bookmarks", side_effect=serialize),
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.archive_bookmarks([bookmark2.id, bookmark1.id], self.user)

        before, after = querysets
        self.assertTrue(before.query.select_for_update)
        self.assertEqual(("id",), before.query.order_by)
        # Reading the state after the change does not need to lock again
        self.assertFalse(after.query.select_for_update)

    def test_locks_tags_before_resolving_their_bookmarks(self):
        tag = self.setup_tag()
        bookmark = self.setup_bookmark(tags=[tag])
        locked_querysets = []
        original_select_for_update = type(Bookmark.objects.all()).select_for_update

        def select_for_update(queryset, *args, **kwargs):
            locked_querysets.append(queryset.model)
            return original_select_for_update(queryset, *args, **kwargs)

        with (
            mock.patch.object(
                type(Bookmark.objects.all()), "select_for_update", select_for_update
            ),
            self.captureOnCommitCallbacks(execute=True),
            tag_service.track_tag_changes([tag]),
        ):
            tag.name = "renamed"
            tag.save()

        self.assertEqual(["Tag", "Bookmark"], [m.__name__ for m in locked_querysets])
        self.assertEqual([(UPDATED, bookmark.id)], self.get_sent_events())

    def test_tag_merge_locks_target_tag(self):
        # Merging adds the target tag to bookmarks, so it has to be locked like
        # the merged tags
        target = self.setup_tag(name="target")
        merged = self.setup_tag(name="merged")
        tracked_tags = []
        original_track_tag_changes = tag_service.track_tag_changes

        def track_tag_changes(tags):
            tracked_tags.extend(tags)
            return original_track_tag_changes(tags)

        self.client.force_login(self.user)
        with mock.patch.object(
            tag_service, "track_tag_changes", side_effect=track_tag_changes
        ):
            self.client.post(
                reverse("linkding:tags.merge"),
                {"target_tag": "target", "merge_tags": "merged"},
            )

        self.assertCountEqual([target.id, merged.id], [tag.id for tag in tracked_tags])

    def test_admin_form_locks_tags_before_bookmark(self):
        self.client.force_login(self.setup_superuser())
        tag = self.setup_tag()
        bookmark = self.setup_bookmark(tags=[tag])
        calls = []
        original_lock_tags = tasks.BookmarkChanges.lock_tags
        original_track = tasks.BookmarkChanges.track

        def lock_tags(changes, tags):
            calls.append(("lock_tags", [t.id for t in tags]))
            return original_lock_tags(changes, tags)

        def track(changes, bookmark_ids):
            calls.append(("track", list(bookmark_ids)))
            return original_track(changes, bookmark_ids)

        url = reverse("admin:bookmarks_bookmark_change", args=[bookmark.id])
        with (
            mock.patch.object(tasks.BookmarkChanges, "lock_tags", lock_tags),
            mock.patch.object(tasks.BookmarkChanges, "track", track),
        ):
            response = self.client.get(url)
            data = {
                "url": bookmark.url,
                "title": "Changed",
                "owner": str(self.user.id),
                "tags": [str(tag.id)],
                "date_added_0": bookmark.date_added.strftime("%Y-%m-%d"),
                "date_added_1": bookmark.date_added.strftime("%H:%M:%S"),
                "date_modified_0": bookmark.date_modified.strftime("%Y-%m-%d"),
                "date_modified_1": bookmark.date_modified.strftime("%H:%M:%S"),
            }
            response = self.client.post(url, data)

        self.assertEqual(302, response.status_code)
        self.assertEqual([("lock_tags", [tag.id]), ("track", [bookmark.id])], calls)

    def test_tracking_queries_do_not_depend_on_number_of_bookmarks(self):
        tag = self.setup_tag()

        def count_queries(number_of_bookmarks: int) -> int:
            ids = [
                self.setup_bookmark(tags=[tag]).id for _ in range(number_of_bookmarks)
            ]
            with (
                CaptureQueriesContext(connection) as context,
                self.captureOnCommitCallbacks(execute=False),
            ):
                bookmark_service.mark_bookmarks_as_unread(ids, self.user)
            return len(context.captured_queries)

        self.assertEqual(count_queries(2), count_queries(20))


class WebhookMessageConsistencyTestCase(WebhookTestMixin, TestCase):
    def test_multiple_events_from_one_operation(self):
        second_webhook = self.setup_webhook(url="https://example.com/second")
        bookmark = self.setup_bookmark()

        with (
            self.captureOnCommitCallbacks(execute=True),
            tasks.track_bookmark_changes(self.user, [bookmark.id]),
        ):
            bookmark.title = "Changed"
            bookmark.is_archived = True
            bookmark.save()

        calls = self.mock_post.call_args_list
        messages = [
            (
                call.args[0],
                call.kwargs["headers"]["webhook-id"],
                json.loads(call.kwargs["data"]),
            )
            for call in calls
        ]
        # One message per event and webhook
        self.assertCountEqual(
            [
                (self.webhook.url, UPDATED),
                (self.webhook.url, ARCHIVED),
                (second_webhook.url, UPDATED),
                (second_webhook.url, ARCHIVED),
            ],
            [(url, body["type"]) for url, _, body in messages],
        )
        # Each message has its own ID, for deduplicating retries
        self.assertEqual(4, len({message_id for _, message_id, _ in messages}))
        # All messages share the timestamp and data of the change
        self.assertEqual(1, len({body["timestamp"] for _, _, body in messages}))
        self.assertEqual(1, len({json.dumps(body["data"]) for _, _, body in messages}))

    def test_timestamps_increase_for_consecutive_changes(self):
        bookmark = self.setup_bookmark()

        def current():
            return Bookmark.objects.get(id=bookmark.id)

        for action in [
            lambda: bookmark_service.archive_bookmark(current()),
            lambda: bookmark_service.mark_bookmarks_as_unread([bookmark.id], self.user),
            lambda: bookmark_service.unarchive_bookmark(current()),
            lambda: bookmark_service.delete_bookmark(current()),
        ]:
            with self.captureOnCommitCallbacks(execute=True):
                action()

        timestamps = [body["timestamp"] for body in self.get_sent_bodies()]
        self.assertEqual(4, len(timestamps))
        self.assertEqual(sorted(timestamps), timestamps)
        self.assertEqual(4, len(set(timestamps)))

    def test_retries_keep_payload_timestamp(self):
        # The payload timestamp is when the change happened, the header
        # timestamp is when the delivery was attempted
        bookmark = self.setup_bookmark()
        self.mock_post.return_value = mock.Mock(status_code=500)

        with (
            mock.patch("time.time", return_value=1000),
            self.assertLogs("bookmarks.services.tasks", "WARNING"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.archive_bookmark(bookmark)
        retry = huey.scheduled()[0]
        self.mock_post.return_value = mock.Mock(status_code=200)
        with mock.patch("time.time", return_value=2000):
            huey.execute(retry, timestamp=retry.eta)

        first, second = self.mock_post.call_args_list
        self.assertEqual(first.kwargs["data"], second.kwargs["data"])
        self.assertEqual(
            first.kwargs["headers"]["webhook-id"],
            second.kwargs["headers"]["webhook-id"],
        )
        self.assertEqual("1000", first.kwargs["headers"]["webhook-timestamp"])
        self.assertEqual("2000", second.kwargs["headers"]["webhook-timestamp"])


class WebhookStaleInstanceTestCase(WebhookTestMixin, TestCase):
    """
    Operations that change specific fields must not revert changes that were
    made since the bookmark was loaded, which would also be reported as
    misleading events.
    """

    def change_in_background(self, bookmark):
        Bookmark.objects.filter(id=bookmark.id).update(
            title="Changed in background", unread=True
        )

    def assertOnlyReports(self, bookmark, event):
        stored = Bookmark.objects.get(id=bookmark.id)
        self.assertEqual("Changed in background", stored.title)
        self.assertTrue(stored.unread)
        self.assertEqual([(event, bookmark.id)], self.get_sent_events())

    def test_archive_and_unarchive(self):
        for action, event in [
            (bookmark_service.archive_bookmark, ARCHIVED),
            (bookmark_service.unarchive_bookmark, Webhook.EVENT_BOOKMARK_UNARCHIVED),
        ]:
            self.mock_post.reset_mock()
            bookmark = Bookmark.objects.get(
                id=self.setup_bookmark(is_archived=event != ARCHIVED).id
            )
            self.change_in_background(bookmark)

            with self.captureOnCommitCallbacks(execute=True):
                action(bookmark)

            self.assertOnlyReports(bookmark, event)

    def test_view_actions(self):
        self.client.force_login(self.user)
        original_bookmark_write = access.bookmark_write
        for action, state in [
            ("unshare", {"shared": True}),
            ("update_state", {"is_archived": False}),
        ]:
            self.mock_post.reset_mock()
            bookmark = self.setup_bookmark(**state)

            def bookmark_write(request, bookmark_id, bookmark=bookmark):
                loaded = original_bookmark_write(request, bookmark_id)
                self.change_in_background(bookmark)
                return loaded

            with (
                mock.patch.object(access, "bookmark_write", bookmark_write),
                self.captureOnCommitCallbacks(execute=True),
            ):
                data = {action: bookmark.id}
                if action == "update_state":
                    # Keep the concurrent change to the read state
                    data.update({"is_archived": "on", "unread": "on"})
                self.client.post(reverse("linkding:bookmarks.index.action"), data)

            stored = Bookmark.objects.get(id=bookmark.id)
            self.assertEqual("Changed in background", stored.title, action)

    def test_assets_do_not_revert_concurrent_changes(self):
        # Creating snapshots can take minutes, during which users can change
        # the bookmark. Reverting such changes would not send any events, as
        # asset operations do not track changes.
        self.setup_temp_assets_dir()
        bookmark = self.setup_bookmark()

        def create_snapshot(url, filepath):
            self.change_in_background(bookmark)
            with open(filepath, "w") as file:
                file.write("<html></html>")

        with (
            mock.patch(
                "bookmarks.services.singlefile.create_snapshot",
                side_effect=create_snapshot,
            ),
            mock.patch(
                "bookmarks.services.assets.detect_content_type",
                return_value="text/html",
            ),
            mock.patch(
                "bookmarks.services.assets.is_pdf_content_type", return_value=False
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            snapshot = assets.create_snapshot_asset(bookmark)
            snapshot.save()
            assets.create_snapshot(snapshot)

            stored = Bookmark.objects.get(id=bookmark.id)
            self.assertEqual("Changed in background", stored.title)
            self.assertEqual(snapshot, stored.latest_snapshot)

            # Uploading and removing assets with a stale bookmark
            stale = Bookmark.objects.get(id=bookmark.id)
            Bookmark.objects.filter(id=bookmark.id).update(title="Changed again")
            upload = SimpleUploadedFile("file.txt", b"content", "text/plain")
            uploaded = assets.upload_asset(stale, upload)
            uploaded.bookmark = stale
            assets.remove_asset(uploaded)

        self.assertEqual("Changed again", Bookmark.objects.get(id=bookmark.id).title)
        self.mock_post.assert_not_called()


class WebhookEditOnlyChangesEditedFieldsTestCase(WebhookTestMixin, TestCase):
    """
    Edits must only change, and report, the fields that they edit. Another
    change that is committed after an edit loaded the bookmark, but before it
    saves it, must neither be reverted nor reported as part of the edit.
    """

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.other_tag = self.setup_tag(name="other")
        self.bookmark = self.setup_bookmark(title="Title", tags=[self.setup_tag()])

    def change_concurrently(self):
        Bookmark.objects.filter(id=self.bookmark.id).update(
            is_archived=True, web_archive_snapshot_url="https://web.archive.org/x"
        )
        self.bookmark.tags.add(self.other_tag)

    def patch_loading(self, target, attribute):
        original = getattr(target, attribute)

        def load(*args, **kwargs):
            result = original(*args, **kwargs)
            self.change_concurrently()
            return result

        return mock.patch.object(target, attribute, load)

    def assertEditReportedOnly(self, **edited_fields):
        stored = Bookmark.objects.get(id=self.bookmark.id)
        self.assertTrue(stored.is_archived)
        self.assertEqual("https://web.archive.org/x", stored.web_archive_snapshot_url)
        self.assertIn("other", stored.tag_names)
        for field, value in edited_fields.items():
            self.assertEqual(value, getattr(stored, field))
        # The edit is reported as an update, not as unarchiving the bookmark
        self.assertEqual([(UPDATED, self.bookmark.id)], self.get_sent_events())
        self.assertTrue(self.get_sent_bodies()[0]["data"]["is_archived"])

    def api_client(self):
        token = ApiToken(user=self.user, name="Test")
        token.save()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        return client

    def test_api_patch(self):
        client = self.api_client()
        with (
            self.patch_loading(BookmarkViewSet, "get_object"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = client.patch(
                reverse("linkding:bookmark-detail", args=[self.bookmark.id]),
                {"title": "Patched"},
                format="json",
            )
        self.assertEqual(200, response.status_code)

        self.assertEditReportedOnly(title="Patched")

    def test_api_put(self):
        client = self.api_client()
        with (
            self.patch_loading(BookmarkViewSet, "get_object"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = client.put(
                reverse("linkding:bookmark-detail", args=[self.bookmark.id]),
                {"url": self.bookmark.url, "title": "Replaced"},
                format="json",
            )
        self.assertEqual(200, response.status_code)

        self.assertEditReportedOnly(title="Replaced")

    def test_edit_form(self):
        with (
            self.patch_loading(access, "bookmark_write"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                reverse("linkding:bookmarks.edit", args=[self.bookmark.id]),
                {
                    "url": self.bookmark.url,
                    "title": "Edited",
                    "tag_string": " ".join(self.bookmark.tag_names + ["other"]),
                },
            )
        self.assertEqual(302, response.status_code)

        self.assertEditReportedOnly(title="Edited")

    def test_adding_existing_bookmark(self):
        with (
            # Runs after the existing bookmark has been loaded
            self.patch_loading(bookmark_service, "_merge_bookmark_data"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.create_bookmark(
                Bookmark(url=self.bookmark.url, title="Added again"),
                " ".join(self.bookmark.tag_names + ["other"]).replace(" ", ","),
                self.user,
            )

        self.assertEditReportedOnly(title="Added again")


class WebhookBackgroundTaskTestCase(WebhookTestMixin, ImportTestMixin, TestCase):
    def test_refresh_metadata_does_not_revert_concurrent_changes(self):
        # The bookmark is archived while its metadata is loaded. Saving the
        # stale bookmark would revert that, and report it as unarchived.
        bookmark = self.setup_bookmark(title="Title")

        def load_metadata(url):
            Bookmark.objects.filter(id=bookmark.id).update(is_archived=True)
            return website_loader.WebsiteMetadata(
                url=url, title="New title", description=None, preview_image=None
            )

        with (
            mock.patch.object(
                tasks, "load_website_metadata", side_effect=load_metadata
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.refresh_bookmarks_metadata([bookmark.id], self.user)

        bookmark.refresh_from_db()
        self.assertTrue(bookmark.is_archived)
        self.assertEqual("New title", bookmark.title)
        self.assertEqual([(UPDATED, bookmark.id)], self.get_sent_events())
        self.assertTrue(self.get_sent_bodies()[0]["data"]["is_archived"])

    def test_import_does_not_report_bookmarks_created_concurrently(self):
        concurrent = {}
        original_track = tasks.track_bookmark_changes

        def track(user, bookmark_ids=()):
            # Another request creates a bookmark for a URL in the import batch
            # after the import looked up existing bookmarks
            if not concurrent:
                concurrent["created"] = True
                concurrent["bookmark"] = bookmark_service.create_bookmark(
                    Bookmark(url="https://example.com/1"), "", self.user
                )
            return original_track(user, bookmark_ids)

        html = self.render_html(
            tags=[BookmarkHtmlTag(href="https://example.com/1", title="Imported")]
        )
        with (
            mock.patch.object(tasks, "track_bookmark_changes", side_effect=track),
            self.captureOnCommitCallbacks(execute=True),
        ):
            importer.import_netscape_html(html, self.user)

        imported = Bookmark.objects.exclude(id=concurrent["bookmark"].id).get(
            url="https://example.com/1"
        )
        # Each bookmark is reported once, by the operation that created it
        self.assertCountEqual(
            [
                (Webhook.EVENT_BOOKMARK_CREATED, concurrent["bookmark"].id),
                (Webhook.EVENT_BOOKMARK_CREATED, imported.id),
            ],
            self.get_sent_events(),
        )
