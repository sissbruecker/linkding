import base64
import hashlib
import hmac
import json
from unittest import mock

from django.test import TestCase, override_settings

from bookmarks.models import Bookmark, Webhook
from bookmarks.services import http_client, webhooks
from bookmarks.tests.helpers import BookmarkFactoryMixin, disable_logging


class WebhooksServiceTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.post_patcher = mock.patch.object(http_client, "post")
        self.mock_post = self.post_patcher.start()
        self.mock_post.return_value = mock.Mock(status_code=200)

    def tearDown(self):
        self.post_patcher.stop()

    def test_generate_secret(self):
        secret = Webhook.generate_secret()

        self.assertTrue(secret.startswith("whsec_"))
        self.assertEqual(32, len(base64.b64decode(secret.removeprefix("whsec_"))))
        self.assertNotEqual(secret, Webhook.generate_secret())

    def test_generates_secret_on_save(self):
        webhook = self.setup_webhook()

        self.assertTrue(webhook.secret.startswith("whsec_"))

    def test_sign(self):
        # Test vector from the Standard Webhooks specification
        signature = webhooks.sign(
            "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw",
            "msg_p5jXN8AQM9LWM0D4loKWxJek",
            1614265330,
            '{"test": 2432232314}',
        )

        self.assertEqual("v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE=", signature)

    def test_serialize_bookmark(self):
        tag1 = self.setup_tag(name="tag2")
        tag2 = self.setup_tag(name="tag1")
        bookmark = self.setup_bookmark(
            url="https://example.com",
            title="Title",
            description="Description",
            notes="Notes",
            web_archive_snapshot_url="https://web.archive.org/example",
            unread=True,
            shared=True,
            tags=[tag1, tag2],
        )

        data = webhooks.serialize_bookmark(bookmark)

        self.assertEqual(
            {
                "id": bookmark.id,
                "url": "https://example.com",
                "title": "Title",
                "description": "Description",
                "notes": "Notes",
                "web_archive_snapshot_url": "https://web.archive.org/example",
                "is_archived": False,
                "unread": True,
                "shared": True,
                "tag_names": ["tag1", "tag2"],
                "date_added": bookmark.date_added.isoformat().replace("+00:00", "Z"),
                "date_modified": bookmark.date_modified.isoformat().replace(
                    "+00:00", "Z"
                ),
            },
            data,
        )

    def test_serialize_bookmarks(self):
        tag1 = self.setup_tag(name="b")
        tag2 = self.setup_tag(name="a")
        bookmark1 = self.setup_bookmark(
            tags=[tag1, tag2],
            web_archive_snapshot_url="https://web.archive.org/example",
            unread=True,
            shared=True,
            is_archived=True,
        )
        bookmark2 = self.setup_bookmark()

        with self.assertNumQueries(2):
            data = webhooks.serialize_bookmarks(
                Bookmark.objects.filter(id__in=[bookmark1.id, bookmark2.id]).order_by(
                    "id"
                )
            )

        # Must match serializing individual bookmarks exactly, as both are
        # compared to detect changes
        self.assertEqual(
            [
                webhooks.serialize_bookmark(bookmark1),
                webhooks.serialize_bookmark(bookmark2),
            ],
            data,
        )
        self.assertEqual(list(webhooks.serialize_bookmark(bookmark1)), list(data[0]))

    def create_bookmark_data(self, **fields) -> dict:
        data = {
            "id": 1,
            "url": "https://example.com",
            "title": "Title",
            "description": "Description",
            "notes": "Notes",
            "web_archive_snapshot_url": "",
            "is_archived": False,
            "unread": False,
            "shared": False,
            "tag_names": ["tag1"],
            "date_added": "2026-01-01T00:00:00Z",
            "date_modified": "2026-01-01T00:00:00Z",
        }
        data.update(fields)
        return data

    def test_get_change_events_created_and_deleted(self):
        data = self.create_bookmark_data()

        self.assertEqual(
            [Webhook.EVENT_BOOKMARK_CREATED], webhooks.get_change_events(None, data)
        )
        self.assertEqual(
            [Webhook.EVENT_BOOKMARK_DELETED], webhooks.get_change_events(data, None)
        )
        self.assertEqual([], webhooks.get_change_events(None, None))

    def test_get_change_events_without_changes(self):
        before = self.create_bookmark_data()

        self.assertEqual([], webhooks.get_change_events(before, dict(before)))

        # The modification date alone does not count as a change
        after = self.create_bookmark_data(date_modified="2026-02-01T00:00:00Z")
        self.assertEqual([], webhooks.get_change_events(before, after))

    def test_get_change_events_updated(self):
        before = self.create_bookmark_data()
        changes = {
            "url": "https://example.com/changed",
            "title": "Changed",
            "description": "Changed",
            "notes": "Changed",
            "web_archive_snapshot_url": "https://web.archive.org/changed",
            "unread": True,
            "shared": True,
            "tag_names": ["tag1", "tag2"],
            "date_added": "2025-01-01T00:00:00Z",
        }

        for field, value in changes.items():
            after = self.create_bookmark_data(**{field: value})
            self.assertEqual(
                [Webhook.EVENT_BOOKMARK_UPDATED],
                webhooks.get_change_events(before, after),
                msg=field,
            )

    def test_get_change_events_archived_and_unarchived(self):
        unarchived = self.create_bookmark_data(is_archived=False)
        archived = self.create_bookmark_data(
            is_archived=True, date_modified="2026-02-01T00:00:00Z"
        )

        self.assertEqual(
            [Webhook.EVENT_BOOKMARK_ARCHIVED],
            webhooks.get_change_events(unarchived, archived),
        )
        self.assertEqual(
            [Webhook.EVENT_BOOKMARK_UNARCHIVED],
            webhooks.get_change_events(archived, unarchived),
        )

    def test_get_change_events_combined(self):
        before = self.create_bookmark_data()
        after = self.create_bookmark_data(title="Changed", is_archived=True)

        self.assertEqual(
            [Webhook.EVENT_BOOKMARK_UPDATED, Webhook.EVENT_BOOKMARK_ARCHIVED],
            webhooks.get_change_events(before, after),
        )

    def test_create_messages(self):
        webhook1 = self.setup_webhook()
        webhook2 = self.setup_webhook()
        data1 = self.create_bookmark_data(id=1)
        data2 = self.create_bookmark_data(id=2)

        messages = webhooks.create_messages(
            self.get_or_create_test_user(),
            [
                (Webhook.EVENT_BOOKMARK_CREATED, data1),
                (Webhook.EVENT_BOOKMARK_DELETED, data2),
            ],
        )

        self.assertEqual(
            [webhook1.id, webhook2.id, webhook1.id, webhook2.id],
            [message.webhook_id for message in messages],
        )
        # Each message has a unique ID
        self.assertEqual(4, len({message.message_id for message in messages}))
        for message in messages:
            self.assertTrue(message.message_id.startswith("msg_"))

        body1 = json.loads(messages[0].body)
        self.assertEqual(Webhook.EVENT_BOOKMARK_CREATED, body1["type"])
        self.assertIn("timestamp", body1)
        self.assertEqual(data1, body1["data"])
        self.assertEqual(messages[0].body, messages[1].body)

        body2 = json.loads(messages[2].body)
        self.assertEqual(Webhook.EVENT_BOOKMARK_DELETED, body2["type"])
        self.assertEqual(data2, body2["data"])

    def test_create_messages_only_for_subscribed_webhooks(self):
        created = self.setup_webhook(events=[Webhook.EVENT_BOOKMARK_CREATED])
        deleted = self.setup_webhook(events=[Webhook.EVENT_BOOKMARK_DELETED])
        self.setup_webhook(enabled=False)
        self.setup_webhook(user=self.setup_user())

        messages = webhooks.create_messages(
            self.get_or_create_test_user(),
            [
                (Webhook.EVENT_BOOKMARK_CREATED, self.create_bookmark_data(id=1)),
                (Webhook.EVENT_BOOKMARK_UPDATED, self.create_bookmark_data(id=2)),
                (Webhook.EVENT_BOOKMARK_DELETED, self.create_bookmark_data(id=3)),
            ],
        )

        self.assertEqual(
            [(created.id, 1), (deleted.id, 3)],
            [
                (message.webhook_id, json.loads(message.body)["data"]["id"])
                for message in messages
            ],
        )

    def test_deliver(self):
        webhook = self.setup_webhook(url="https://example.com/hook")
        body = '{"type": "bookmark.created"}'

        with mock.patch("time.time", return_value=1700000000):
            webhooks.deliver(webhook, "msg_123", body)

        self.mock_post.assert_called_once()
        args, kwargs = self.mock_post.call_args
        self.assertEqual(("https://example.com/hook",), args)
        self.assertEqual(body.encode(), kwargs["data"])
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(webhooks.DELIVERY_TIMEOUT, kwargs["timeout"])

        headers = kwargs["headers"]
        self.assertEqual("application/json", headers["Content-Type"])
        self.assertTrue(headers["User-Agent"].startswith("linkding/"))
        self.assertEqual("msg_123", headers["webhook-id"])
        self.assertEqual("1700000000", headers["webhook-timestamp"])

        # Verify signature the way a receiver would
        key = base64.b64decode(webhook.secret.removeprefix("whsec_"))
        content = f"msg_123.1700000000.{body}".encode()
        expected = base64.b64encode(
            hmac.new(key, content, hashlib.sha256).digest()
        ).decode()
        self.assertEqual(f"v1,{expected}", headers["webhook-signature"])

    def test_deliver_records_success(self):
        webhook = self.setup_webhook()
        self.mock_post.return_value = mock.Mock(status_code=204)

        webhooks.deliver(webhook, "msg_123", "{}")

        webhook.refresh_from_db()
        self.assertIsNotNone(webhook.last_delivery_date)
        self.assertEqual(Webhook.DELIVERY_STATUS_SUCCESS, webhook.last_delivery_status)
        self.assertEqual("HTTP 204", webhook.last_delivery_message)

    def test_deliver_fails_on_non_success_status(self):
        webhook = self.setup_webhook()

        for status_code in [301, 400, 404, 500, 503]:
            self.mock_post.return_value = mock.Mock(status_code=status_code)

            with self.assertRaises(webhooks.WebhookDeliveryError):
                webhooks.deliver(webhook, "msg_123", "{}")

            webhook.refresh_from_db()
            self.assertEqual(
                Webhook.DELIVERY_STATUS_FAILURE, webhook.last_delivery_status
            )
            self.assertEqual(f"HTTP {status_code}", webhook.last_delivery_message)

    def test_deliver_fails_on_request_error(self):
        webhook = self.setup_webhook()
        self.mock_post.side_effect = http_client.RequestException("Connection error")

        with self.assertRaises(http_client.RequestException):
            webhooks.deliver(webhook, "msg_123", "{}")

        webhook.refresh_from_db()
        self.assertEqual(Webhook.DELIVERY_STATUS_FAILURE, webhook.last_delivery_status)
        self.assertEqual("Connection error", webhook.last_delivery_message)

    def test_deliver_truncates_long_error_messages(self):
        webhook = self.setup_webhook()
        self.mock_post.side_effect = http_client.RequestException("x" * 1000)

        with self.assertRaises(http_client.RequestException):
            webhooks.deliver(webhook, "msg_123", "{}")

        webhook.refresh_from_db()
        self.assertEqual(512, len(webhook.last_delivery_message))

    def test_deliver_does_not_overwrite_other_changes(self):
        webhook = self.setup_webhook(name="Initial name")
        Webhook.objects.filter(id=webhook.id).update(name="Changed name")

        webhooks.deliver(webhook, "msg_123", "{}")

        webhook.refresh_from_db()
        self.assertEqual("Changed name", webhook.name)

    @disable_logging
    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="")
    def test_deliver_blocks_internal_hosts(self):
        self.post_patcher.stop()
        http_client.get_allowlist.cache_clear()
        webhook = self.setup_webhook(url="http://127.0.0.1:1/webhook")

        try:
            with self.assertRaises(http_client.BlockedAddressError):
                webhooks.deliver(webhook, "msg_123", "{}")
        finally:
            http_client.get_allowlist.cache_clear()
            self.post_patcher.start()

        webhook.refresh_from_db()
        self.assertEqual(Webhook.DELIVERY_STATUS_FAILURE, webhook.last_delivery_status)
        self.assertIn("LD_ALLOWED_INTERNAL_HOSTS", webhook.last_delivery_message)

    def test_send_test_message(self):
        webhook = self.setup_webhook(events=[], enabled=False)

        webhooks.send_test_message(webhook)

        self.mock_post.assert_called_once()
        body = json.loads(self.mock_post.call_args.kwargs["data"])
        self.assertEqual("webhook.test", body["type"])
        self.assertIn("message", body["data"])
