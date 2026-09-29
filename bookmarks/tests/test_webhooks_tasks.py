import io
import ipaddress
import json
from unittest import mock

from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from huey.contrib.djhuey import HUEY as huey
from rest_framework.test import APIClient

from bookmarks.models import ApiToken, Bookmark, Webhook
from bookmarks.services import bookmarks as bookmark_service
from bookmarks.services import http_client, tasks, website_loader
from bookmarks.tests.helpers import (
    BookmarkFactoryMixin,
    disable_logging,
)


class WebhookTestMixin(BookmarkFactoryMixin):
    def setUp(self):
        huey.immediate = True
        huey.results = True
        huey.store_none = True

        self.post_patcher = mock.patch.object(http_client, "post")
        self.mock_post = self.post_patcher.start()
        self.mock_post.return_value = mock.Mock(status_code=200)

        self.webhook = self.setup_webhook()

    def tearDown(self):
        self.post_patcher.stop()
        huey.storage.flush_results()
        huey.storage.flush_schedule()
        huey.immediate = False

    def get_sent_events(self) -> list[tuple[str, int]]:
        events = []
        for call in self.mock_post.call_args_list:
            body = json.loads(call.kwargs["data"])
            events.append((body["type"], body["data"]["id"]))
        return events

    def get_sent_bodies(self) -> list[dict]:
        return [
            json.loads(call.kwargs["data"]) for call in self.mock_post.call_args_list
        ]


class WebhookTasksTestCase(WebhookTestMixin, TestCase):
    def test_track_changes_delivers_after_commit(self):
        bookmark = self.setup_bookmark()

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            with tasks.track_bookmark_changes(self.user, [bookmark.id]):
                bookmark.title = "Changed"
                bookmark.save()
            # Nothing is sent before the outer transaction commits
            self.mock_post.assert_not_called()

        for callback in callbacks:
            callback()

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        self.assertEqual(self.webhook.url, self.mock_post.call_args.args[0])

    def test_track_changes_created(self):
        with (
            self.captureOnCommitCallbacks(execute=True),
            tasks.track_bookmark_changes(self.user) as changes,
        ):
            bookmark = self.setup_bookmark()
            changes.track_created(bookmark)

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_CREATED, bookmark.id)], self.get_sent_events()
        )

    def test_track_changes_without_changes(self):
        bookmark = self.setup_bookmark()

        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            tasks.track_bookmark_changes(self.user, [bookmark.id]),
        ):
            bookmark.save()

        self.assertEqual(0, len(callbacks))
        self.mock_post.assert_not_called()

    def test_track_changes_rolls_back_on_error(self):
        class ChangeError(Exception):
            pass

        bookmark = self.setup_bookmark(title="Initial")

        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            self.assertRaises(ChangeError),
            tasks.track_bookmark_changes(self.user, [bookmark.id]),
        ):
            bookmark.title = "Changed"
            bookmark.save()
            raise ChangeError()

        self.assertEqual(0, len(callbacks))
        self.mock_post.assert_not_called()
        bookmark.refresh_from_db()
        self.assertEqual("Initial", bookmark.title)

    def test_track_changes_does_not_deliver_when_outer_transaction_rolls_back(self):
        bookmark = self.setup_bookmark()

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    with tasks.track_bookmark_changes(self.user, [bookmark.id]):
                        bookmark.title = "Changed"
                        bookmark.save()
                    # The tracked change completed, but the outer transaction
                    # is rolled back afterwards
                    raise Exception("Rollback")
            except Exception:
                pass

        self.assertEqual(0, len(callbacks))
        self.mock_post.assert_not_called()

    def test_track_changes_only_tracks_bookmarks_of_user(self):
        other_bookmark = self.setup_bookmark(user=self.setup_user())

        with (
            self.captureOnCommitCallbacks(execute=True),
            tasks.track_bookmark_changes(self.user, [other_bookmark.id]),
        ):
            other_bookmark.title = "Changed"
            other_bookmark.save()

        self.mock_post.assert_not_called()

    def test_track_changes_only_sends_subscribed_events(self):
        self.webhook.events = [Webhook.EVENT_BOOKMARK_ARCHIVED]
        self.webhook.save()
        bookmark = self.setup_bookmark()

        with (
            self.captureOnCommitCallbacks(execute=True),
            tasks.track_bookmark_changes(self.user, [bookmark.id]),
        ):
            bookmark.title = "Changed"
            bookmark.is_archived = True
            bookmark.save()

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id)], self.get_sent_events()
        )

    def assertDoesNotTrack(self):
        bookmark_ids = mock.MagicMock()

        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            tasks.track_bookmark_changes(self.user, bookmark_ids) as changes,
        ):
            changes.track_created(self.setup_bookmark())

        # Does not evaluate the lazy list of bookmarks to track
        bookmark_ids.__iter__.assert_not_called()
        self.assertFalse(changes.enabled)
        self.assertEqual(0, len(callbacks))
        self.mock_post.assert_not_called()

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_track_changes_does_nothing_when_background_tasks_disabled(self):
        self.assertDoesNotTrack()

    def test_track_changes_does_nothing_without_webhooks(self):
        self.webhook.delete()
        self.setup_webhook(user=self.setup_user())

        self.assertDoesNotTrack()

    def test_track_changes_does_nothing_with_only_disabled_webhooks(self):
        self.webhook.enabled = False
        self.webhook.save()

        self.assertDoesNotTrack()

    def test_track_changes_without_webhooks_uses_single_query(self):
        self.webhook.delete()
        bookmark = self.setup_bookmark()

        # Only checks for webhooks, without starting a transaction
        with (
            self.assertNumQueries(1),
            tasks.track_bookmark_changes(self.user, [bookmark.id]),
        ):
            pass

    def test_track_changes_of_all_owners(self):
        other_user = self.setup_user()
        other_webhook = self.setup_webhook(
            user=other_user, url="https://example.com/other"
        )
        own = self.setup_bookmark()
        other = self.setup_bookmark(user=other_user)

        with (
            self.captureOnCommitCallbacks(execute=True),
            tasks.track_bookmark_changes_of_all_owners([own.id, other.id]),
        ):
            Bookmark.objects.update(unread=True)

        urls_by_bookmark = {
            json.loads(call.kwargs["data"])["data"]["id"]: call.args[0]
            for call in self.mock_post.call_args_list
        }
        self.assertEqual(
            {own.id: self.webhook.url, other.id: other_webhook.url}, urls_by_bookmark
        )

    def test_deliver_task_skips_deleted_webhook(self):
        webhook_id = self.webhook.id
        self.webhook.delete()

        tasks._deliver_webhook_task(webhook_id, "msg_123", "{}")

        self.mock_post.assert_not_called()

    def test_deliver_task_skips_disabled_webhook(self):
        self.webhook.enabled = False
        self.webhook.save()

        tasks._deliver_webhook_task(self.webhook.id, "msg_123", "{}")

        self.mock_post.assert_not_called()

    @disable_logging
    def test_deliver_task_retries_on_error_response(self):
        self.mock_post.return_value = mock.Mock(status_code=500)

        tasks._deliver_webhook_task(self.webhook.id, "msg_123", "{}")

        self.assertEqual(1, huey.scheduled_count())
        retry = huey.scheduled()[0]
        self.assertEqual(4, retry.retries)
        self.assertEqual(60, retry.retry_delay)
        # Retries use the same message ID and body
        self.assertEqual((self.webhook.id, "msg_123", "{}"), retry.args)

    @disable_logging
    def test_deliver_task_retries_on_request_error(self):
        self.mock_post.side_effect = http_client.RequestException("Timeout")

        tasks._deliver_webhook_task(self.webhook.id, "msg_123", "{}")

        self.assertEqual(1, huey.scheduled_count())

    @disable_logging
    def test_deliver_task_does_not_retry_blocked_address(self):
        self.mock_post.side_effect = http_client.BlockedAddressError(
            "localhost", ipaddress.ip_address("127.0.0.1")
        )

        tasks._deliver_webhook_task(self.webhook.id, "msg_123", "{}")

        self.assertEqual(0, huey.scheduled_count())

    def test_deliver_task_does_not_retry_on_success(self):
        tasks._deliver_webhook_task(self.webhook.id, "msg_123", "{}")

        self.mock_post.assert_called_once()
        self.assertEqual(0, huey.scheduled_count())


class WebhookBookmarkServiceEventsTestCase(WebhookTestMixin, TestCase):
    def test_create_bookmark(self):
        with self.captureOnCommitCallbacks(execute=True):
            bookmark = bookmark_service.create_bookmark(
                Bookmark(url="https://example.com"), "tag1,tag2", self.user
            )

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_CREATED, bookmark.id)], self.get_sent_events()
        )
        data = self.get_sent_bodies()[0]["data"]
        self.assertEqual("https://example.com", data["url"])
        self.assertEqual(["tag1", "tag2"], data["tag_names"])

    def test_create_bookmark_with_existing_url(self):
        bookmark = self.setup_bookmark(url="https://example.com")

        with self.captureOnCommitCallbacks(execute=True):
            bookmark_service.create_bookmark(
                Bookmark(url="https://example.com", title="New title"), "", self.user
            )

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        self.assertEqual("New title", self.get_sent_bodies()[0]["data"]["title"])

    def test_update_bookmark(self):
        bookmark = self.setup_bookmark()
        bookmark.title = "Updated title"

        with self.captureOnCommitCallbacks(execute=True):
            bookmark_service.update_bookmark(bookmark, "tag1", self.user)

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        data = self.get_sent_bodies()[0]["data"]
        self.assertEqual("Updated title", data["title"])
        self.assertEqual(["tag1"], data["tag_names"])

    def test_archive_and_unarchive_bookmark(self):
        bookmark = self.setup_bookmark()

        with self.captureOnCommitCallbacks(execute=True):
            bookmark_service.archive_bookmark(bookmark)
        with self.captureOnCommitCallbacks(execute=True):
            bookmark_service.unarchive_bookmark(bookmark)

        self.assertEqual(
            [
                (Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id),
                (Webhook.EVENT_BOOKMARK_UNARCHIVED, bookmark.id),
            ],
            self.get_sent_events(),
        )
        bodies = self.get_sent_bodies()
        self.assertTrue(bodies[0]["data"]["is_archived"])
        self.assertFalse(bodies[1]["data"]["is_archived"])

    def test_delete_bookmark(self):
        tag = self.setup_tag(name="tag1")
        bookmark = self.setup_bookmark(title="Deleted bookmark", tags=[tag])
        bookmark_id = bookmark.id

        with self.captureOnCommitCallbacks(execute=True):
            bookmark_service.delete_bookmark(bookmark)

        self.assertFalse(Bookmark.objects.filter(id=bookmark_id).exists())
        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_DELETED, bookmark_id)], self.get_sent_events()
        )
        data = self.get_sent_bodies()[0]["data"]
        self.assertEqual("Deleted bookmark", data["title"])
        self.assertEqual(["tag1"], data["tag_names"])

    def test_bulk_delete(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        other_user_bookmark = self.setup_bookmark(user=self.setup_user())

        with self.captureOnCommitCallbacks(execute=True):
            bookmark_service.delete_bookmarks(
                [bookmark1.id, bookmark2.id, other_user_bookmark.id], self.user
            )

        self.assertCountEqual(
            [
                (Webhook.EVENT_BOOKMARK_DELETED, bookmark1.id),
                (Webhook.EVENT_BOOKMARK_DELETED, bookmark2.id),
            ],
            self.get_sent_events(),
        )

    def test_bulk_actions(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        other_user_bookmark = self.setup_bookmark(user=self.setup_user())
        ids = [bookmark1.id, str(bookmark2.id), other_user_bookmark.id]

        actions = [
            (
                lambda: bookmark_service.archive_bookmarks(ids, self.user),
                Webhook.EVENT_BOOKMARK_ARCHIVED,
                lambda data: data["is_archived"],
            ),
            (
                lambda: bookmark_service.unarchive_bookmarks(ids, self.user),
                Webhook.EVENT_BOOKMARK_UNARCHIVED,
                lambda data: not data["is_archived"],
            ),
            (
                lambda: bookmark_service.tag_bookmarks(ids, "newtag", self.user),
                Webhook.EVENT_BOOKMARK_UPDATED,
                lambda data: data["tag_names"] == ["newtag"],
            ),
            (
                lambda: bookmark_service.untag_bookmarks(ids, "newtag", self.user),
                Webhook.EVENT_BOOKMARK_UPDATED,
                lambda data: data["tag_names"] == [],
            ),
            (
                lambda: bookmark_service.mark_bookmarks_as_unread(ids, self.user),
                Webhook.EVENT_BOOKMARK_UPDATED,
                lambda data: data["unread"],
            ),
            (
                lambda: bookmark_service.mark_bookmarks_as_read(ids, self.user),
                Webhook.EVENT_BOOKMARK_UPDATED,
                lambda data: not data["unread"],
            ),
            (
                lambda: bookmark_service.share_bookmarks(ids, self.user),
                Webhook.EVENT_BOOKMARK_UPDATED,
                lambda data: data["shared"],
            ),
            (
                lambda: bookmark_service.unshare_bookmarks(ids, self.user),
                Webhook.EVENT_BOOKMARK_UPDATED,
                lambda data: not data["shared"],
            ),
        ]

        for action, expected_event, check_data in actions:
            self.mock_post.reset_mock()

            with self.captureOnCommitCallbacks(execute=True):
                action()

            self.assertCountEqual(
                [(expected_event, bookmark1.id), (expected_event, bookmark2.id)],
                self.get_sent_events(),
            )
            # Messages contain the state after the change
            for body in self.get_sent_bodies():
                self.assertTrue(check_data(body["data"]), msg=expected_event)

    def test_refresh_metadata(self):
        bookmark = self.setup_bookmark()

        with (
            mock.patch.object(
                tasks,
                "load_website_metadata",
                return_value=website_loader.WebsiteMetadata(
                    url=bookmark.url,
                    title="Refreshed title",
                    description="Refreshed description",
                    preview_image=None,
                ),
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            bookmark_service.refresh_bookmarks_metadata([bookmark.id], self.user)

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        self.assertEqual("Refreshed title", self.get_sent_bodies()[0]["data"]["title"])

    def test_other_users_webhooks_are_not_called(self):
        other_user = self.setup_user()
        self.webhook.owner = other_user
        self.webhook.save()

        with self.captureOnCommitCallbacks(execute=True):
            bookmark_service.create_bookmark(
                Bookmark(url="https://example.com"), "", self.user
            )

        self.mock_post.assert_not_called()


class WebhookViewEventsTestCase(WebhookTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def post_action(self, data: dict):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("linkding:bookmarks.index.action"), data
            )
        self.assertEqual(302, response.status_code)

    def test_new_bookmark(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("linkding:bookmarks.new"),
                {"url": "https://example.com", "tag_string": "tag1"},
            )

        bookmark = Bookmark.objects.get(url="https://example.com")
        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_CREATED, bookmark.id)], self.get_sent_events()
        )

    def test_edit_bookmark(self):
        bookmark = self.setup_bookmark()

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("linkding:bookmarks.edit", args=[bookmark.id]),
                {"url": bookmark.url, "title": "Edited", "tag_string": ""},
            )

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )

    def test_remove(self):
        bookmark = self.setup_bookmark()

        self.post_action({"remove": bookmark.id})

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_DELETED, bookmark.id)], self.get_sent_events()
        )

    def test_archive_and_unarchive(self):
        bookmark = self.setup_bookmark()

        self.post_action({"archive": bookmark.id})
        self.post_action({"unarchive": bookmark.id})

        self.assertEqual(
            [
                (Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id),
                (Webhook.EVENT_BOOKMARK_UNARCHIVED, bookmark.id),
            ],
            self.get_sent_events(),
        )

    def test_mark_as_read(self):
        bookmark = self.setup_bookmark(unread=True)

        self.post_action({"mark_as_read": bookmark.id})

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        self.assertFalse(self.get_sent_bodies()[0]["data"]["unread"])

    def test_unshare(self):
        bookmark = self.setup_bookmark(shared=True)

        self.post_action({"unshare": bookmark.id})

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        self.assertFalse(self.get_sent_bodies()[0]["data"]["shared"])

    def test_update_state(self):
        bookmark = self.setup_bookmark()

        # Archiving
        self.post_action({"update_state": bookmark.id, "is_archived": "on"})
        # Other state changes
        self.post_action(
            {"update_state": bookmark.id, "is_archived": "on", "unread": "on"}
        )
        # Unarchiving
        self.post_action({"update_state": bookmark.id, "unread": "on"})

        self.assertEqual(
            [
                (Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id),
                (Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id),
                (Webhook.EVENT_BOOKMARK_UNARCHIVED, bookmark.id),
            ],
            self.get_sent_events(),
        )

    def test_bulk_delete(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()

        self.post_action(
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bookmark_id": [str(bookmark1.id), str(bookmark2.id)],
            }
        )

        self.assertCountEqual(
            [
                (Webhook.EVENT_BOOKMARK_DELETED, bookmark1.id),
                (Webhook.EVENT_BOOKMARK_DELETED, bookmark2.id),
            ],
            self.get_sent_events(),
        )

    def test_new_bookmark_with_existing_url(self):
        bookmark = self.setup_bookmark(url="https://example.com")

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("linkding:bookmarks.new"),
                {"url": "https://example.com", "tag_string": ""},
            )

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )

    def test_bulk_action_across_filtered_pages(self):
        # Bulk actions across all pages resolve the bookmarks from a filtered
        # query. Messages must still be sent for bookmarks that no longer match
        # the filter after the change.
        unread1 = self.setup_bookmark(unread=True)
        unread2 = self.setup_bookmark(unread=True)
        read = self.setup_bookmark(unread=False)

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("linkding:bookmarks.index.action") + "?unread=yes",
                {
                    "bulk_action": ["bulk_read"],
                    "bulk_execute": [""],
                    "bulk_select_across": ["on"],
                },
            )

        self.assertCountEqual(
            [
                (Webhook.EVENT_BOOKMARK_UPDATED, unread1.id),
                (Webhook.EVENT_BOOKMARK_UPDATED, unread2.id),
            ],
            self.get_sent_events(),
        )
        self.assertNotIn(read.id, [event[1] for event in self.get_sent_events()])

    def test_bulk_unarchive_in_archived_view(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("linkding:bookmarks.archived.action"),
                {
                    "bulk_action": ["bulk_unarchive"],
                    "bulk_execute": [""],
                    "bookmark_id": [str(bookmark1.id), str(bookmark2.id)],
                },
            )

        self.assertCountEqual(
            [
                (Webhook.EVENT_BOOKMARK_UNARCHIVED, bookmark1.id),
                (Webhook.EVENT_BOOKMARK_UNARCHIVED, bookmark2.id),
            ],
            self.get_sent_events(),
        )

    def test_unshare_in_shared_view(self):
        self.user.profile.enable_sharing = True
        self.user.profile.save()
        bookmark = self.setup_bookmark(shared=True)

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("linkding:bookmarks.shared.action"), {"unshare": bookmark.id}
            )

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )

    def test_actions_on_other_users_bookmarks_send_no_events(self):
        other_user = self.setup_user()
        self.setup_webhook(user=other_user)
        bookmark = self.setup_bookmark(user=other_user)

        with self.captureOnCommitCallbacks(execute=True):
            for action in ["archive", "remove", "mark_as_read", "update_state"]:
                self.client.post(
                    reverse("linkding:bookmarks.index.action"), {action: bookmark.id}
                )

        self.mock_post.assert_not_called()
        self.assertTrue(Bookmark.objects.filter(id=bookmark.id).exists())


class WebhookApiEventsTestCase(WebhookTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        token = ApiToken(user=self.user, name="Test")
        token.save()
        self.api_client = APIClient()
        self.api_client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        self.metadata_patcher = mock.patch.object(
            website_loader,
            "load_website_metadata",
            return_value=website_loader.WebsiteMetadata(
                url="https://example.com",
                title="Scraped title",
                description="Scraped description",
                preview_image=None,
            ),
        )
        self.metadata_patcher.start()

    def tearDown(self):
        self.metadata_patcher.stop()
        super().tearDown()

    def test_create_includes_scraped_metadata(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api_client.post(
                reverse("linkding:bookmark-list"),
                {"url": "https://example.com"},
                format="json",
            )
        self.assertEqual(201, response.status_code)
        self.assertEqual("Scraped title", response.data["title"])

        bookmark = Bookmark.objects.get(url="https://example.com")
        self.assertEqual("Scraped title", bookmark.title)
        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_CREATED, bookmark.id)], self.get_sent_events()
        )
        data = self.get_sent_bodies()[0]["data"]
        self.assertEqual("Scraped title", data["title"])
        self.assertEqual("Scraped description", data["description"])

    def test_create_with_scraping_disabled(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.post(
                reverse("linkding:bookmark-list") + "?disable_scraping",
                {"url": "https://example.com"},
                format="json",
            )

        self.assertEqual("", self.get_sent_bodies()[0]["data"]["title"])

    def test_update(self):
        bookmark = self.setup_bookmark()

        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.patch(
                reverse("linkding:bookmark-detail", args=[bookmark.id]),
                {"title": "Patched"},
                format="json",
            )

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        self.assertEqual("Patched", self.get_sent_bodies()[0]["data"]["title"])

    def test_archive_and_unarchive(self):
        bookmark = self.setup_bookmark()

        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.post(
                reverse("linkding:bookmark-archive", args=[bookmark.id])
            )
        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.post(
                reverse("linkding:bookmark-unarchive", args=[bookmark.id])
            )

        self.assertEqual(
            [
                (Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id),
                (Webhook.EVENT_BOOKMARK_UNARCHIVED, bookmark.id),
            ],
            self.get_sent_events(),
        )

    def test_delete(self):
        bookmark = self.setup_bookmark()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.api_client.delete(
                reverse("linkding:bookmark-detail", args=[bookmark.id])
            )
        self.assertEqual(204, response.status_code)

        self.assertFalse(Bookmark.objects.filter(id=bookmark.id).exists())
        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_DELETED, bookmark.id)], self.get_sent_events()
        )

    def test_put(self):
        bookmark = self.setup_bookmark()

        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.put(
                reverse("linkding:bookmark-detail", args=[bookmark.id]),
                {"url": bookmark.url, "title": "Replaced", "tag_names": ["tag1"]},
                format="json",
            )

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        data = self.get_sent_bodies()[0]["data"]
        self.assertEqual("Replaced", data["title"])
        self.assertEqual(["tag1"], data["tag_names"])

    def test_patch_is_archived(self):
        # Archiving through an edit sends the same event as the archive action,
        # so that webhooks that are only subscribed to archive events get it
        bookmark = self.setup_bookmark()
        url = reverse("linkding:bookmark-detail", args=[bookmark.id])

        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.patch(url, {"is_archived": True}, format="json")
        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.patch(url, {"is_archived": True}, format="json")
        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.patch(url, {"is_archived": False}, format="json")

        self.assertEqual(
            [
                (Webhook.EVENT_BOOKMARK_ARCHIVED, bookmark.id),
                # Repeating the edit does not change anything
                (Webhook.EVENT_BOOKMARK_UNARCHIVED, bookmark.id),
            ],
            self.get_sent_events(),
        )

    def test_create_with_existing_url(self):
        bookmark = self.setup_bookmark(url="https://example.com", title="Old title")

        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.post(
                reverse("linkding:bookmark-list"),
                {"url": "https://example.com"},
                format="json",
            )

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_UPDATED, bookmark.id)], self.get_sent_events()
        )
        self.assertEqual("Scraped title", self.get_sent_bodies()[0]["data"]["title"])

    def create_singlefile_upload_body(self):
        file = io.BytesIO(b"dummy content")
        file.name = "snapshot.html"
        return {"url": "https://example.com", "file": file}

    @mock.patch("bookmarks.services.assets.upload_snapshot")
    def test_singlefile_upload_creates_bookmark(self, _):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api_client.post(
                reverse("linkding:bookmark-singlefile"),
                self.create_singlefile_upload_body(),
                format="multipart",
            )
        self.assertEqual(201, response.status_code)

        bookmark = Bookmark.objects.get(url="https://example.com")
        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_CREATED, bookmark.id)], self.get_sent_events()
        )
        self.assertEqual("Scraped title", self.get_sent_bodies()[0]["data"]["title"])

    @mock.patch("bookmarks.services.assets.upload_snapshot")
    def test_singlefile_upload_for_existing_bookmark(self, _):
        # Uploading a snapshot does not change the bookmark data
        self.setup_bookmark(url="https://example.com")

        with self.captureOnCommitCallbacks(execute=True):
            self.api_client.post(
                reverse("linkding:bookmark-singlefile"),
                self.create_singlefile_upload_body(),
                format="multipart",
            )

        self.mock_post.assert_not_called()


class WebhookAdminEventsTestCase(WebhookTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.setup_superuser())
        self.other_user = self.setup_user()
        self.other_webhook = self.setup_webhook(
            user=self.other_user, url="https://example.com/other"
        )

    def post_admin_action(self, action: str, bookmarks: list[Bookmark]):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("admin:bookmarks_bookmark_changelist"),
                {
                    "action": action,
                    "index": 0,
                    "_selected_action": [str(bookmark.id) for bookmark in bookmarks],
                },
            )
        self.assertEqual(302, response.status_code)

    def get_sent_events_by_url(self) -> dict[str, list[tuple[str, int]]]:
        events = {}
        for call in self.mock_post.call_args_list:
            body = json.loads(call.kwargs["data"])
            events.setdefault(call.args[0], []).append(
                (body["type"], body["data"]["id"])
            )
        return events

    def assertEventsPerOwner(self, event: str, own: Bookmark, other: Bookmark):
        # Each owner's webhooks only receive messages about their own bookmarks
        events = self.get_sent_events_by_url()
        self.assertEqual([(event, own.id)], events[self.webhook.url])
        self.assertEqual([(event, other.id)], events[self.other_webhook.url])

    def test_delete(self):
        own = self.setup_bookmark()
        other = self.setup_bookmark(user=self.other_user)

        self.post_admin_action("delete_selected_bookmarks", [own, other])

        self.assertEqual(0, Bookmark.objects.count())
        self.assertEventsPerOwner(Webhook.EVENT_BOOKMARK_DELETED, own, other)

    def test_archive(self):
        own = self.setup_bookmark()
        other = self.setup_bookmark(user=self.other_user)

        self.post_admin_action("archive_selected_bookmarks", [own, other])

        self.assertEventsPerOwner(Webhook.EVENT_BOOKMARK_ARCHIVED, own, other)

    def test_unarchive(self):
        own = self.setup_bookmark(is_archived=True)
        other = self.setup_bookmark(is_archived=True, user=self.other_user)

        self.post_admin_action("unarchive_selected_bookmarks", [own, other])

        self.assertEventsPerOwner(Webhook.EVENT_BOOKMARK_UNARCHIVED, own, other)

    def test_mark_as_read(self):
        own = self.setup_bookmark(unread=True)
        other = self.setup_bookmark(unread=True, user=self.other_user)

        self.post_admin_action("mark_as_read", [own, other])

        self.assertEventsPerOwner(Webhook.EVENT_BOOKMARK_UPDATED, own, other)
        for body in self.get_sent_bodies():
            self.assertFalse(body["data"]["unread"])

    def test_mark_as_read_in_filtered_list(self):
        # The action's queryset is filtered by read state, so it no longer
        # matches the bookmarks after the update
        own = self.setup_bookmark(unread=True)
        other = self.setup_bookmark(unread=True, user=self.other_user)
        self.setup_bookmark(unread=False)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("admin:bookmarks_bookmark_changelist") + "?unread__exact=1",
                {
                    "action": "mark_as_read",
                    "index": 0,
                    "select_across": 1,
                    "_selected_action": [str(own.id)],
                },
            )
        self.assertEqual(302, response.status_code)

        self.assertEventsPerOwner(Webhook.EVENT_BOOKMARK_UPDATED, own, other)

    def test_mark_as_unread(self):
        own = self.setup_bookmark()
        other = self.setup_bookmark(user=self.other_user)

        self.post_admin_action("mark_as_unread", [own, other])

        self.assertEventsPerOwner(Webhook.EVENT_BOOKMARK_UPDATED, own, other)
        for body in self.get_sent_bodies():
            self.assertTrue(body["data"]["unread"])


class WebhookDeliveryOrderTestCase(WebhookTestMixin, TransactionTestCase):
    """
    Requests run in autocommit mode, where on_commit callbacks run immediately
    instead of being deferred like in TestCase. Messages must only be delivered
    once the change is persisted, so that receivers that call back into the API
    see the new state.
    """

    def setUp(self):
        super().setUp()
        self.states_at_delivery = []

        def record_state(url, **kwargs):
            body = json.loads(kwargs["data"])
            bookmark = Bookmark.objects.filter(id=body["data"]["id"]).first()
            self.states_at_delivery.append((body["type"], bookmark))
            return mock.Mock(status_code=200)

        self.mock_post.side_effect = record_state

    def test_created(self):
        bookmark = bookmark_service.create_bookmark(
            Bookmark(url="https://example.com"), "tag1", self.user
        )

        [(event, stored)] = self.states_at_delivery
        self.assertEqual(Webhook.EVENT_BOOKMARK_CREATED, event)
        self.assertEqual(bookmark.id, stored.id)
        self.assertEqual(["tag1"], stored.tag_names)

    def test_archived(self):
        bookmark = self.setup_bookmark()

        bookmark_service.archive_bookmark(bookmark)

        [(event, stored)] = self.states_at_delivery
        self.assertEqual(Webhook.EVENT_BOOKMARK_ARCHIVED, event)
        self.assertTrue(stored.is_archived)

    def test_bulk_updated(self):
        bookmark = self.setup_bookmark()

        bookmark_service.mark_bookmarks_as_unread([bookmark.id], self.user)

        [(event, stored)] = self.states_at_delivery
        self.assertEqual(Webhook.EVENT_BOOKMARK_UPDATED, event)
        self.assertTrue(stored.unread)

    def test_deleted(self):
        bookmark = self.setup_bookmark()

        bookmark_service.delete_bookmark(bookmark)

        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_DELETED, None)], self.states_at_delivery
        )

    def test_bulk_deleted(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()

        bookmark_service.delete_bookmarks([bookmark1.id, bookmark2.id], self.user)

        self.assertEqual(
            [
                (Webhook.EVENT_BOOKMARK_DELETED, None),
                (Webhook.EVENT_BOOKMARK_DELETED, None),
            ],
            self.states_at_delivery,
        )

    def test_deleted_through_api(self):
        bookmark = self.setup_bookmark()
        token = ApiToken(user=self.user, name="Test")
        token.save()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = client.delete(
            reverse("linkding:bookmark-detail", args=[bookmark.id])
        )

        self.assertEqual(204, response.status_code)
        self.assertEqual(
            [(Webhook.EVENT_BOOKMARK_DELETED, None)], self.states_at_delivery
        )

    def test_failed_delete_sends_no_event(self):
        class DeleteError(Exception):
            pass

        bookmark = self.setup_bookmark()

        with (
            mock.patch.object(Bookmark, "delete", side_effect=DeleteError),
            self.assertRaises(DeleteError),
        ):
            bookmark_service.delete_bookmark(bookmark)

        self.assertEqual([], self.states_at_delivery)
