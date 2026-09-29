"""
Tests that webhook events consistently reflect the actual state changes of
bookmarks, regardless of the operation that caused them: repeated actions and
edits without changes send nothing, combined edits send an event for each kind
of change, and indirect changes, such as renaming tags, importing bookmarks or
background tasks updating bookmarks, are reported like any other change.
"""

import datetime
import functools
import json
from unittest import mock

import waybackpy
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from bookmarks.models import ApiToken, Bookmark, Tag, UserProfile, Webhook
from bookmarks.services import bookmarks as bookmark_service
from bookmarks.services import importer, tasks, website_loader
from bookmarks.tests.helpers import BookmarkHtmlTag, HtmlTestMixin, ImportTestMixin
from bookmarks.tests.test_webhooks_tasks import WebhookTestMixin

CREATED = Webhook.EVENT_BOOKMARK_CREATED
UPDATED = Webhook.EVENT_BOOKMARK_UPDATED
DELETED = Webhook.EVENT_BOOKMARK_DELETED
ARCHIVED = Webhook.EVENT_BOOKMARK_ARCHIVED
UNARCHIVED = Webhook.EVENT_BOOKMARK_UNARCHIVED


class WebhookConsistencyTestMixin(WebhookTestMixin):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def sent_events(self, action) -> list[tuple[str, int]]:
        """Runs the action and returns the events it sent."""
        self.mock_post.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            action()
        return self.get_sent_events()

    def sent_data(self) -> dict[int, dict]:
        """Returns the latest data that was sent for each bookmark."""
        return {body["data"]["id"]: body["data"] for body in self.get_sent_bodies()}

    def post_action(
        self, data: dict, url_name: str = "linkding:bookmarks.index.action"
    ):
        response = self.client.post(reverse(url_name), data)
        self.assertEqual(302, response.status_code)

    def post_bulk_action(self, action: str, bookmarks: list[Bookmark], **data):
        self.post_action(
            {
                "bulk_action": [action],
                "bulk_execute": [""],
                "bookmark_id": [str(bookmark.id) for bookmark in bookmarks],
                **data,
            }
        )

    def setup_api_client(self) -> APIClient:
        token = ApiToken(user=self.user, name="Test")
        token.save()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        return client


class WebhookRepeatedActionsTestCase(WebhookConsistencyTestMixin, TestCase):
    def test_archive_and_unarchive_are_only_reported_once(self):
        bookmark = self.setup_bookmark()

        def archive():
            bookmark_service.archive_bookmark(bookmark)

        def unarchive():
            bookmark_service.unarchive_bookmark(bookmark)

        self.assertEqual([(ARCHIVED, bookmark.id)], self.sent_events(archive))
        self.assertEqual([], self.sent_events(archive))
        self.assertEqual([(UNARCHIVED, bookmark.id)], self.sent_events(unarchive))
        self.assertEqual([], self.sent_events(unarchive))

    def test_repeated_api_archive_and_unarchive(self):
        client = self.setup_api_client()
        bookmark = self.setup_bookmark()
        archive_url = reverse("linkding:bookmark-archive", args=[bookmark.id])
        unarchive_url = reverse("linkding:bookmark-unarchive", args=[bookmark.id])

        events = []
        for url in [archive_url, archive_url, unarchive_url, unarchive_url]:
            events += self.sent_events(lambda url=url: client.post(url))

        self.assertEqual([(ARCHIVED, bookmark.id), (UNARCHIVED, bookmark.id)], events)

    def test_repeated_view_actions(self):
        bookmark = self.setup_bookmark(unread=True, shared=True)

        for action, event in [
            ("archive", ARCHIVED),
            ("unarchive", UNARCHIVED),
            ("mark_as_read", UPDATED),
            ("unshare", UPDATED),
        ]:
            post = functools.partial(self.post_action, {action: bookmark.id})
            self.assertEqual([(event, bookmark.id)], self.sent_events(post), action)
            self.assertEqual([], self.sent_events(post), action)

    def test_update_state_without_changes(self):
        bookmark = self.setup_bookmark(unread=True)

        events = self.sent_events(
            lambda: self.post_action({"update_state": bookmark.id, "unread": "on"})
        )

        self.assertEqual([], events)

    def test_bulk_actions_only_report_changed_bookmarks(self):
        tag = self.setup_tag(name="tag1")
        cases = [
            ("bulk_archive", {"is_archived": False}, {"is_archived": True}, ARCHIVED),
            (
                "bulk_unarchive",
                {"is_archived": True},
                {"is_archived": False},
                UNARCHIVED,
            ),
            ("bulk_read", {"unread": True}, {"unread": False}, UPDATED),
            ("bulk_unread", {"unread": False}, {"unread": True}, UPDATED),
            ("bulk_share", {"shared": False}, {"shared": True}, UPDATED),
            ("bulk_unshare", {"shared": True}, {"shared": False}, UPDATED),
            ("bulk_tag", {"tags": []}, {"tags": [tag]}, UPDATED),
            ("bulk_untag", {"tags": [tag]}, {"tags": []}, UPDATED),
        ]

        for action, changing_state, unchanged_state, event in cases:
            changing = self.setup_bookmark(**changing_state)
            unchanged = self.setup_bookmark(**unchanged_state)
            bulk_action = functools.partial(
                self.post_bulk_action,
                action,
                [changing, unchanged],
                bulk_tag_string="tag1",
            )

            self.assertEqual(
                [(event, changing.id)], self.sent_events(bulk_action), action
            )
            # Repeating the action does not change anything
            self.assertEqual([], self.sent_events(bulk_action), action)

    def test_edit_form_without_changes(self):
        tag = self.setup_tag(name="tag1")
        bookmark = self.setup_bookmark(title="Title", tags=[tag])

        events = self.sent_events(
            lambda: self.client.post(
                reverse("linkding:bookmarks.edit", args=[bookmark.id]),
                {
                    "url": bookmark.url,
                    "title": "Title",
                    "description": bookmark.description,
                    "notes": bookmark.notes,
                    "tag_string": "tag1",
                },
            )
        )

        self.assertEqual([], events)

    def test_adding_existing_bookmark_with_same_data(self):
        bookmark = self.setup_bookmark(title="Title")

        events = self.sent_events(
            lambda: bookmark_service.create_bookmark(
                Bookmark(url=bookmark.url, title="Title"), "", self.user
            )
        )

        self.assertEqual([], events)

    def test_api_update_without_changes(self):
        client = self.setup_api_client()
        bookmark = self.setup_bookmark(title="Title")

        events = self.sent_events(
            lambda: client.patch(
                reverse("linkding:bookmark-detail", args=[bookmark.id]),
                {"title": "Title"},
                format="json",
            )
        )

        self.assertEqual([], events)


class WebhookCombinedEditsTestCase(WebhookConsistencyTestMixin, TestCase):
    def test_update_state_archive_and_other_changes(self):
        bookmark = self.setup_bookmark()

        events = self.sent_events(
            lambda: self.post_action(
                {
                    "update_state": bookmark.id,
                    "is_archived": "on",
                    "unread": "on",
                    "shared": "on",
                }
            )
        )

        self.assertEqual([(UPDATED, bookmark.id), (ARCHIVED, bookmark.id)], events)
        data = self.sent_data()[bookmark.id]
        self.assertTrue(data["is_archived"])
        self.assertTrue(data["unread"])
        self.assertTrue(data["shared"])

    def test_update_state_unarchive_and_other_changes(self):
        bookmark = self.setup_bookmark(is_archived=True, unread=True)

        events = self.sent_events(
            lambda: self.post_action({"update_state": bookmark.id})
        )

        self.assertEqual([(UPDATED, bookmark.id), (UNARCHIVED, bookmark.id)], events)

    def test_api_patch_archive_and_edit(self):
        client = self.setup_api_client()
        bookmark = self.setup_bookmark(title="Title")

        events = self.sent_events(
            lambda: client.patch(
                reverse("linkding:bookmark-detail", args=[bookmark.id]),
                {"title": "Changed", "is_archived": True},
                format="json",
            )
        )

        self.assertEqual([(UPDATED, bookmark.id), (ARCHIVED, bookmark.id)], events)
        data = self.sent_data()[bookmark.id]
        self.assertEqual("Changed", data["title"])
        self.assertTrue(data["is_archived"])

    def test_api_put_unarchive_and_edit(self):
        client = self.setup_api_client()
        bookmark = self.setup_bookmark(is_archived=True)

        events = self.sent_events(
            lambda: client.put(
                reverse("linkding:bookmark-detail", args=[bookmark.id]),
                {"url": bookmark.url, "is_archived": False, "tag_names": ["new"]},
                format="json",
            )
        )

        self.assertEqual([(UPDATED, bookmark.id), (UNARCHIVED, bookmark.id)], events)
        self.assertEqual(["new"], self.sent_data()[bookmark.id]["tag_names"])

    def test_webhooks_receive_the_events_they_are_subscribed_to(self):
        self.webhook.delete()
        updated_webhook = self.setup_webhook(
            url="https://example.com/updated", events=[UPDATED]
        )
        archived_webhook = self.setup_webhook(
            url="https://example.com/archived", events=[ARCHIVED]
        )
        bookmark = self.setup_bookmark()

        self.sent_events(
            lambda: self.post_action(
                {"update_state": bookmark.id, "is_archived": "on", "unread": "on"}
            )
        )

        received = [
            (call.args[0], event)
            for call, event in zip(
                self.mock_post.call_args_list,
                [event for event, _ in self.get_sent_events()],
                strict=True,
            )
        ]
        self.assertCountEqual(
            [(updated_webhook.url, UPDATED), (archived_webhook.url, ARCHIVED)],
            received,
        )


class WebhookTagChangesTestCase(WebhookConsistencyTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tag = self.setup_tag(name="tag1")
        self.other_tag = self.setup_tag(name="tag2")
        self.tagged1 = self.setup_bookmark(tags=[self.tag])
        self.tagged2 = self.setup_bookmark(tags=[self.tag, self.other_tag])
        self.untagged = self.setup_bookmark(tags=[self.other_tag])
        # Tag with the same name of another user, whose webhook must not be
        # called
        self.other_user = self.setup_user()
        self.setup_webhook(user=self.other_user, url="https://example.com/other")
        other_user_tag = self.setup_tag(user=self.other_user, name="tag1")
        self.setup_bookmark(user=self.other_user, tags=[other_user_tag])

    def assertTaggedBookmarksUpdated(self, events, expected_tag_names):
        self.assertCountEqual(
            [(UPDATED, self.tagged1.id), (UPDATED, self.tagged2.id)], events
        )
        self.assertNotIn(
            "https://example.com/other",
            [call.args[0] for call in self.mock_post.call_args_list],
        )
        data = self.sent_data()
        self.assertEqual(expected_tag_names[0], data[self.tagged1.id]["tag_names"])
        self.assertEqual(expected_tag_names[1], data[self.tagged2.id]["tag_names"])

    def rename_tag(self, name: str):
        response = self.client.post(
            reverse("linkding:tags.edit", args=[self.tag.id]), {"name": name}
        )
        self.assertEqual(302, response.status_code)

    def test_rename_tag(self):
        events = self.sent_events(lambda: self.rename_tag("renamed"))

        self.assertTaggedBookmarksUpdated(events, [["renamed"], ["renamed", "tag2"]])

    def test_rename_tag_capitalization(self):
        events = self.sent_events(lambda: self.rename_tag("Tag1"))

        self.assertTaggedBookmarksUpdated(events, [["Tag1"], ["Tag1", "tag2"]])

    def test_save_tag_without_changes(self):
        events = self.sent_events(lambda: self.rename_tag("tag1"))

        self.assertEqual([], events)

    def test_delete_tag(self):
        events = self.sent_events(
            lambda: self.client.post(
                reverse("linkding:tags.index"), {"delete_tag": self.tag.id}
            )
        )

        self.assertTaggedBookmarksUpdated(events, [[], ["tag2"]])

    def test_delete_tag_through_api(self):
        client = self.setup_api_client()

        events = self.sent_events(
            lambda: client.delete(reverse("linkding:tag-detail", args=[self.tag.id]))
        )

        self.assertFalse(Tag.objects.filter(id=self.tag.id).exists())
        self.assertTaggedBookmarksUpdated(events, [[], ["tag2"]])

    def test_merge_tags(self):
        target = self.setup_tag(name="target")
        merge = self.setup_tag(name="merge")
        with_merge_tag = self.setup_bookmark(tags=[merge])
        with_both_tags = self.setup_bookmark(tags=[merge, target])
        with_target_tag = self.setup_bookmark(tags=[target])

        events = self.sent_events(
            lambda: self.client.post(
                reverse("linkding:tags.merge"),
                {"target_tag": "target", "merge_tags": "merge tag1"},
            )
        )

        # Bookmarks that only had the target tag do not change
        self.assertCountEqual(
            [
                (UPDATED, self.tagged1.id),
                (UPDATED, self.tagged2.id),
                (UPDATED, with_merge_tag.id),
                (UPDATED, with_both_tags.id),
            ],
            events,
        )
        self.assertNotIn(with_target_tag.id, [event[1] for event in events])
        data = self.sent_data()
        self.assertEqual(["tag2", "target"], data[self.tagged2.id]["tag_names"])
        self.assertEqual(["target"], data[with_merge_tag.id]["tag_names"])
        self.assertEqual(["target"], data[with_both_tags.id]["tag_names"])

    def test_bulk_tag_multiple_bookmarks(self):
        bookmarks = [self.tagged1, self.tagged2, self.untagged]

        events = self.sent_events(
            lambda: self.post_bulk_action(
                "bulk_tag", bookmarks, bulk_tag_string="tag2 tag3"
            )
        )

        self.assertCountEqual(
            [
                (UPDATED, self.tagged1.id),
                (UPDATED, self.tagged2.id),
                (UPDATED, self.untagged.id),
            ],
            events,
        )
        data = self.sent_data()
        self.assertEqual(["tag1", "tag2", "tag3"], data[self.tagged1.id]["tag_names"])
        self.assertEqual(["tag2", "tag3"], data[self.untagged.id]["tag_names"])

    def test_bulk_untag_multiple_bookmarks(self):
        bookmarks = [self.tagged1, self.tagged2, self.untagged]

        events = self.sent_events(
            lambda: self.post_bulk_action(
                "bulk_untag", bookmarks, bulk_tag_string="tag1"
            )
        )

        # The bookmark without the tag does not change
        self.assertTaggedBookmarksUpdated(events, [[], ["tag2"]])


class WebhookAsyncUpdatesTestCase(WebhookConsistencyTestMixin, TestCase):
    def test_refresh_metadata(self):
        bookmark = self.setup_bookmark(title="Title", description="Description")

        def refresh(title: str):
            metadata = website_loader.WebsiteMetadata(
                url=bookmark.url, title=title, description=None, preview_image=None
            )
            with mock.patch.object(
                tasks, "load_website_metadata", return_value=metadata
            ):
                bookmark_service.refresh_bookmarks_metadata([bookmark.id], self.user)

        self.assertEqual([], self.sent_events(lambda: refresh("Title")))
        self.assertEqual(
            [(UPDATED, bookmark.id)], self.sent_events(lambda: refresh("New title"))
        )
        self.assertEqual("New title", self.sent_data()[bookmark.id]["title"])

    def test_web_archive_snapshot(self):
        self.user.profile.web_archive_integration = (
            UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED
        )
        self.user.profile.save()
        snapshot_url = "https://web.archive.org/web/example"
        save_api = mock.Mock(archive_url=snapshot_url)

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=save_api
        ):
            events = self.sent_events(
                lambda: bookmark_service.create_bookmark(
                    Bookmark(url="https://example.com"), "", self.user
                )
            )

        bookmark = Bookmark.objects.get(url="https://example.com")
        self.assertEqual([(CREATED, bookmark.id), (UPDATED, bookmark.id)], events)
        bodies = self.get_sent_bodies()
        self.assertEqual("", bodies[0]["data"]["web_archive_snapshot_url"])
        self.assertEqual(snapshot_url, bodies[1]["data"]["web_archive_snapshot_url"])

    def test_favicons_and_preview_images_do_not_send_events(self):
        # Favicons and preview images are not part of the payload
        self.user.profile.enable_favicons = True
        self.user.profile.enable_preview_images = True
        self.user.profile.save()

        with (
            mock.patch(
                "bookmarks.services.favicon_loader.load_favicon",
                return_value="favicon.png",
            ),
            mock.patch(
                "bookmarks.services.preview_image_loader.load_preview_image",
                return_value="preview.png",
            ),
        ):
            events = self.sent_events(
                lambda: bookmark_service.create_bookmark(
                    Bookmark(url="https://example.com"), "", self.user
                )
            )

        bookmark = Bookmark.objects.get(url="https://example.com")
        self.assertEqual("favicon.png", bookmark.favicon_file)
        self.assertEqual("preview.png", bookmark.preview_image_file)
        self.assertEqual([(CREATED, bookmark.id)], events)


class WebhookImportTestCase(WebhookConsistencyTestMixin, ImportTestMixin, TestCase):
    def import_bookmarks(self, tags: list[BookmarkHtmlTag]):
        html = self.render_html(tags=tags)
        return self.sent_events(lambda: importer.import_netscape_html(html, self.user))

    def test_import_new_bookmarks(self):
        events = self.import_bookmarks(
            [
                BookmarkHtmlTag(href="https://example.com/1", title="One", tags="a,b"),
                BookmarkHtmlTag(href="https://example.com/2", title="Two"),
            ]
        )

        bookmark1 = Bookmark.objects.get(url="https://example.com/1")
        bookmark2 = Bookmark.objects.get(url="https://example.com/2")
        self.assertCountEqual(
            [(CREATED, bookmark1.id), (CREATED, bookmark2.id)], events
        )
        data = self.sent_data()
        self.assertEqual("One", data[bookmark1.id]["title"])
        self.assertEqual(["a", "b"], data[bookmark1.id]["tag_names"])

    def test_import_existing_bookmarks(self):
        added = timezone.now().replace(microsecond=0) - datetime.timedelta(days=1)
        add_date = str(int(added.timestamp()))
        tag = self.setup_tag(name="a")
        unchanged = self.setup_bookmark(
            url="https://example.com/unchanged", title="Same", tags=[tag], added=added
        )
        changed = self.setup_bookmark(
            url="https://example.com/changed", title="Old", added=added
        )
        tagged = self.setup_bookmark(
            url="https://example.com/tagged", title="Same", added=added
        )

        events = self.import_bookmarks(
            [
                BookmarkHtmlTag(
                    href=unchanged.url, title="Same", tags="a", add_date=add_date
                ),
                BookmarkHtmlTag(href=changed.url, title="New", add_date=add_date),
                BookmarkHtmlTag(
                    href=tagged.url, title="Same", tags="a", add_date=add_date
                ),
            ]
        )

        self.assertCountEqual([(UPDATED, changed.id), (UPDATED, tagged.id)], events)
        data = self.sent_data()
        self.assertEqual("New", data[changed.id]["title"])
        self.assertEqual(["a"], data[tagged.id]["tag_names"])

    def test_import_does_not_report_existing_bookmarks_that_fail_to_import(self):
        existing = self.setup_bookmark(url="https://example.com/existing")

        events = self.import_bookmarks(
            [
                # Fails validation, as the title is too long
                BookmarkHtmlTag(href=existing.url, title="x" * 1000),
                BookmarkHtmlTag(href="https://example.com/new", title="New"),
            ]
        )

        new = Bookmark.objects.get(url="https://example.com/new")
        self.assertEqual([(CREATED, new.id)], events)

    def test_import_multiple_batches(self):
        events = self.import_bookmarks(
            [
                BookmarkHtmlTag(href=f"https://example.com/{i}", title=f"{i}")
                for i in range(250)
            ]
        )

        self.assertEqual(250, len(events))
        self.assertEqual({CREATED}, {event for event, _ in events})
        self.assertEqual(250, len({bookmark_id for _, bookmark_id in events}))


class WebhookAdminFormsTestCase(WebhookConsistencyTestMixin, HtmlTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.setup_superuser())

    def get_form_data(self, url: str) -> dict:
        """Returns the data that the admin form at the URL would submit."""
        soup = self.make_soup(self.client.get(url).content.decode())
        form = soup.select_one("form[id$=_form]")
        data = {}
        for field in form.select("input[name], select[name], textarea[name]"):
            name = field["name"]
            if field.name == "select":
                values = [
                    option["value"] for option in field.select("option[selected]")
                ]
                data[name] = values if field.has_attr("multiple") else "".join(values)
            elif field.name == "textarea":
                data[name] = field.text.strip()
            elif field.get("type") == "checkbox":
                if field.has_attr("checked"):
                    data[name] = "on"
            elif field.get("type") != "submit":
                data[name] = field.get("value", "")
        return data

    def submit_bookmark_form(self, bookmark: Bookmark = None, **changes):
        if bookmark:
            url = reverse("admin:bookmarks_bookmark_change", args=[bookmark.id])
        else:
            url = reverse("admin:bookmarks_bookmark_add")
        data = self.get_form_data(url)
        data.update(changes)
        for field, value in changes.items():
            if value is False:
                del data[field]

        response = self.client.post(url, data)
        self.assertEqual(302, response.status_code, response.content.decode()[:2000])

    def test_edit_bookmark(self):
        tag = self.setup_tag(name="tag1")
        bookmark = self.setup_bookmark(title="Title")

        events = self.sent_events(
            lambda: self.submit_bookmark_form(
                bookmark, title="Changed", tags=[str(tag.id)]
            )
        )

        self.assertEqual([(UPDATED, bookmark.id)], events)
        data = self.sent_data()[bookmark.id]
        self.assertEqual("Changed", data["title"])
        # Tags are saved after the bookmark, the event must include them
        self.assertEqual(["tag1"], data["tag_names"])

    def test_edit_bookmark_without_changes(self):
        # The admin form requires bookmarks to have tags. It also only
        # submits dates with second precision, so saving a date with
        # microseconds would actually change the bookmark.
        date = timezone.now().replace(microsecond=0)
        bookmark = self.setup_bookmark(
            tags=[self.setup_tag()], added=date, modified=date
        )

        events = self.sent_events(lambda: self.submit_bookmark_form(bookmark))

        self.assertEqual([], events)

    def test_edit_bookmark_combined_with_archiving(self):
        # The admin form requires bookmarks to have tags
        bookmark = self.setup_bookmark(tags=[self.setup_tag()])

        events = self.sent_events(
            lambda: self.submit_bookmark_form(
                bookmark, title="Changed", is_archived="on"
            )
        )

        self.assertEqual([(UPDATED, bookmark.id), (ARCHIVED, bookmark.id)], events)

    def test_add_bookmark(self):
        tag = self.setup_tag(name="tag1")
        now = timezone.now()

        events = self.sent_events(
            lambda: self.submit_bookmark_form(
                url="https://example.com/admin",
                title="Added in admin",
                owner=str(self.user.id),
                tags=[str(tag.id)],
                date_added_0=now.strftime("%Y-%m-%d"),
                date_added_1=now.strftime("%H:%M:%S"),
                date_modified_0=now.strftime("%Y-%m-%d"),
                date_modified_1=now.strftime("%H:%M:%S"),
            )
        )

        bookmark = Bookmark.objects.get(url="https://example.com/admin")
        self.assertEqual([(CREATED, bookmark.id)], events)
        self.assertEqual(["tag1"], self.sent_data()[bookmark.id]["tag_names"])

    def test_move_bookmark_to_other_user(self):
        other_user = self.setup_user()
        other_webhook = self.setup_webhook(
            user=other_user, url="https://example.com/other"
        )
        # The admin form requires bookmarks to have tags
        bookmark = self.setup_bookmark(tags=[self.setup_tag()])

        self.sent_events(
            lambda: self.submit_bookmark_form(bookmark, owner=str(other_user.id))
        )

        received = {
            call.args[0]: event
            for call, (event, _) in zip(
                self.mock_post.call_args_list, self.get_sent_events(), strict=True
            )
        }
        self.assertEqual(
            {self.webhook.url: DELETED, other_webhook.url: CREATED}, received
        )

    def test_delete_bookmark(self):
        bookmark = self.setup_bookmark()

        events = self.sent_events(
            lambda: self.client.post(
                reverse("admin:bookmarks_bookmark_delete", args=[bookmark.id]),
                {"post": "yes"},
            )
        )

        self.assertFalse(Bookmark.objects.filter(id=bookmark.id).exists())
        self.assertEqual([(DELETED, bookmark.id)], events)

    def test_rename_tag(self):
        tag = self.setup_tag(name="tag1")
        bookmark = self.setup_bookmark(tags=[tag])
        url = reverse("admin:bookmarks_tag_change", args=[tag.id])
        data = self.get_form_data(url)
        data["name"] = "renamed"

        events = self.sent_events(lambda: self.client.post(url, data))

        self.assertEqual([(UPDATED, bookmark.id)], events)
        self.assertEqual(["renamed"], self.sent_data()[bookmark.id]["tag_names"])

    def test_delete_tag(self):
        tag = self.setup_tag(name="tag1")
        bookmark = self.setup_bookmark(tags=[tag])

        events = self.sent_events(
            lambda: self.client.post(
                reverse("admin:bookmarks_tag_delete", args=[tag.id]), {"post": "yes"}
            )
        )

        self.assertFalse(Tag.objects.filter(id=tag.id).exists())
        self.assertEqual([(UPDATED, bookmark.id)], events)

    def test_delete_tags_of_multiple_users(self):
        other_user = self.setup_user()
        other_webhook = self.setup_webhook(
            user=other_user, url="https://example.com/other"
        )
        own_tag = self.setup_tag(name="tag1")
        other_tag = self.setup_tag(user=other_user, name="tag1")
        own = self.setup_bookmark(tags=[own_tag])
        other = self.setup_bookmark(user=other_user, tags=[other_tag])

        self.sent_events(
            lambda: self.client.post(
                reverse("admin:bookmarks_tag_changelist"),
                {
                    "action": "delete_selected",
                    "_selected_action": [str(own_tag.id), str(other_tag.id)],
                    "post": "yes",
                },
            )
        )

        self.assertEqual(0, Tag.objects.count())
        received = {
            call.args[0]: bookmark_id
            for call, (_, bookmark_id) in zip(
                self.mock_post.call_args_list, self.get_sent_events(), strict=True
            )
        }
        self.assertEqual(
            {self.webhook.url: own.id, other_webhook.url: other.id}, received
        )


class WebhookIndirectChangesOrderTestCase(
    WebhookTestMixin, ImportTestMixin, TransactionTestCase
):
    """
    Like WebhookDeliveryOrderTestCase, for indirect changes: messages must only
    be delivered once the change is persisted.
    """

    def setUp(self):
        super().setUp()
        self.tag_names_at_delivery = []

        def record_state(url, **kwargs):
            bookmark_id = json.loads(kwargs["data"])["data"]["id"]
            bookmark = Bookmark.objects.filter(id=bookmark_id).first()
            self.tag_names_at_delivery.append(bookmark.tag_names if bookmark else None)
            return mock.Mock(status_code=200)

        self.mock_post.side_effect = record_state

    def test_rename_tag(self):
        tag = self.setup_tag(name="tag1")
        self.setup_bookmark(tags=[tag])
        self.client.force_login(self.user)

        self.client.post(reverse("linkding:tags.edit", args=[tag.id]), {"name": "new"})

        self.assertEqual([["new"]], self.tag_names_at_delivery)

    def test_import(self):
        html = self.render_html(
            tags=[BookmarkHtmlTag(href="https://example.com", tags="tag1")]
        )

        importer.import_netscape_html(html, self.user)

        self.assertEqual([["tag1"]], self.tag_names_at_delivery)
