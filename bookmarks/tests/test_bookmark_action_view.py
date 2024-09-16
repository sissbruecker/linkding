from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import model_to_dict
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from bookmarks.models import Bookmark, BookmarkAsset
from bookmarks.services import tasks, bookmarks
from bookmarks.tests.helpers import (
    BookmarkFactoryMixin,
    BookmarkListTestMixin,
    TagCloudTestMixin,
)


class BookmarkActionViewTestCase(
    TestCase, BookmarkFactoryMixin, BookmarkListTestMixin, TagCloudTestMixin
):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertBookmarksAreUnmodified(self, bookmarks: [Bookmark]):
        self.assertEqual(len(bookmarks), Bookmark.objects.count())

        for bookmark in bookmarks:
            self.assertEqual(
                model_to_dict(bookmark),
                model_to_dict(Bookmark.objects.get(id=bookmark.id)),
            )

    def test_archive_should_archive_bookmark(self):
        bookmark = self.setup_bookmark()

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "archive": [bookmark.id],
            },
        )

        bookmark.refresh_from_db()

        self.assertTrue(bookmark.is_archived)

    def test_can_only_archive_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark = self.setup_bookmark(user=other_user)

        response = self.client.post(
            reverse("bookmarks:index.action"),
            {
                "archive": [bookmark.id],
            },
        )

        bookmark.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertFalse(bookmark.is_archived)

    def test_unarchive_should_unarchive_bookmark(self):
        bookmark = self.setup_bookmark(is_archived=True)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "unarchive": [bookmark.id],
            },
        )
        bookmark.refresh_from_db()

        self.assertFalse(bookmark.is_archived)

    def test_unarchive_can_only_archive_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark = self.setup_bookmark(is_archived=True, user=other_user)

        response = self.client.post(
            reverse("bookmarks:index.action"),
            {
                "unarchive": [bookmark.id],
            },
        )
        bookmark.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertTrue(bookmark.is_archived)

    def test_delete_should_delete_bookmark(self):
        bookmark = self.setup_bookmark()

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "remove": [bookmark.id],
            },
        )

        self.assertEqual(Bookmark.objects.count(), 0)

    def test_delete_can_only_delete_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark = self.setup_bookmark(user=other_user)

        response = self.client.post(
            reverse("bookmarks:index.action"),
            {
                "remove": [bookmark.id],
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Bookmark.objects.filter(id=bookmark.id).exists())

    def test_mark_as_read(self):
        bookmark = self.setup_bookmark(unread=True)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "mark_as_read": [bookmark.id],
            },
        )
        bookmark.refresh_from_db()

        self.assertFalse(bookmark.unread)

    def test_unshare_should_unshare_bookmark(self):
        bookmark = self.setup_bookmark(shared=True)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "unshare": [bookmark.id],
            },
        )

        bookmark.refresh_from_db()

        self.assertFalse(bookmark.shared)

    def test_can_only_unshare_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        response = self.client.post(
            reverse("bookmarks:index.action"),
            {
                "unshare": [bookmark.id],
            },
        )

        bookmark.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertTrue(bookmark.shared)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot(self):
        bookmark = self.setup_bookmark()
        with patch.object(tasks, "_create_html_snapshot_task"):
            self.client.post(
                reverse("bookmarks:index.action"),
                {
                    "create_html_snapshot": [bookmark.id],
                },
            )
            self.assertEqual(bookmark.bookmarkasset_set.count(), 1)
            asset = bookmark.bookmarkasset_set.first()
            self.assertEqual(asset.asset_type, BookmarkAsset.TYPE_SNAPSHOT)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_can_only_create_html_snapshot_for_own_bookmarks(self):
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        with patch.object(tasks, "_create_html_snapshot_task"):
            response = self.client.post(
                reverse("bookmarks:index.action"),
                {
                    "create_html_snapshot": [bookmark.id],
                },
            )
            self.assertEqual(response.status_code, 404)
            self.assertEqual(bookmark.bookmarkasset_set.count(), 0)

    def test_upload_asset(self):
        bookmark = self.setup_bookmark()
        file_content = b"file content"
        upload_file = SimpleUploadedFile("test.txt", file_content)

        with patch.object(bookmarks, "upload_asset") as mock_upload_asset:
            response = self.client.post(
                reverse("bookmarks:index.action"),
                {"upload_asset": bookmark.id, "upload_asset_file": upload_file},
            )
            self.assertEqual(response.status_code, 302)

            mock_upload_asset.assert_called_once()

            args, _ = mock_upload_asset.call_args
            self.assertEqual(args[0], bookmark)

            upload_file = args[1]
            self.assertEqual(upload_file.name, "test.txt")

    def test_can_only_upload_asset_for_own_bookmarks(self):
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        file_content = b"file content"
        upload_file = SimpleUploadedFile("test.txt", file_content)

        with patch.object(bookmarks, "upload_asset") as mock_upload_asset:
            response = self.client.post(
                reverse("bookmarks:index.action"),
                {"upload_asset": bookmark.id, "upload_asset_file": upload_file},
            )
            self.assertEqual(response.status_code, 404)

            mock_upload_asset.assert_not_called()

    def test_remove_asset(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(bookmark)

        response = self.client.post(
            reverse("bookmarks:index.action"), {"remove_asset": asset.id}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BookmarkAsset.objects.filter(id=asset.id).exists())

    def test_can_only_remove_own_asset(self):
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        asset = self.setup_asset(bookmark)

        response = self.client.post(
            reverse("bookmarks:index.action"), {"remove_asset": asset.id}
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(BookmarkAsset.objects.filter(id=asset.id).exists())

    def test_update_state(self):
        bookmark = self.setup_bookmark()

        response = self.client.post(
            reverse("bookmarks:index.action"),
            {
                "update_state": bookmark.id,
                "is_archived": "on",
                "unread": "on",
                "shared": "on",
            },
        )
        self.assertEqual(response.status_code, 302)

        bookmark.refresh_from_db()
        self.assertTrue(bookmark.unread)
        self.assertTrue(bookmark.is_archived)
        self.assertTrue(bookmark.shared)

    def test_can_only_update_own_bookmark_state(self):
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)

        response = self.client.post(
            reverse("bookmarks:index.action"),
            {
                "update_state": bookmark.id,
                "is_archived": "on",
                "unread": "on",
                "shared": "on",
            },
        )
        self.assertEqual(response.status_code, 404)

        bookmark.refresh_from_db()
        self.assertFalse(bookmark.unread)
        self.assertFalse(bookmark.is_archived)
        self.assertFalse(bookmark.shared)

    def test_bulk_archive(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_archive"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_can_only_bulk_archive_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(user=other_user)
        bookmark2 = self.setup_bookmark(user=other_user)
        bookmark3 = self.setup_bookmark(user=other_user)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_archive"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_bulk_unarchive(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        self.client.post(
            reverse("bookmarks:archived.action"),
            {
                "bulk_action": ["bulk_unarchive"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_can_only_bulk_unarchive_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(is_archived=True, user=other_user)
        bookmark2 = self.setup_bookmark(is_archived=True, user=other_user)
        bookmark3 = self.setup_bookmark(is_archived=True, user=other_user)

        self.client.post(
            reverse("bookmarks:archived.action"),
            {
                "bulk_action": ["bulk_unarchive"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_bulk_delete(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertIsNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark3.id).first())

    def test_can_only_bulk_delete_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(user=other_user)
        bookmark2 = self.setup_bookmark(user=other_user)
        bookmark3 = self.setup_bookmark(user=other_user)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertIsNotNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNotNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNotNone(Bookmark.objects.filter(id=bookmark3.id).first())

    def test_bulk_tag(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_tag"],
                "bulk_execute": [""],
                "bulk_tag_string": [f"{tag1.name} {tag2.name}"],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_can_only_bulk_tag_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(user=other_user)
        bookmark2 = self.setup_bookmark(user=other_user)
        bookmark3 = self.setup_bookmark(user=other_user)
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_tag"],
                "bulk_execute": [""],
                "bulk_tag_string": [f"{tag1.name} {tag2.name}"],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [])

    def test_bulk_untag(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark3 = self.setup_bookmark(tags=[tag1, tag2])

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_untag"],
                "bulk_execute": [""],
                "bulk_tag_string": [f"{tag1.name} {tag2.name}"],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [])

    def test_can_only_bulk_untag_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2], user=other_user)
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2], user=other_user)
        bookmark3 = self.setup_bookmark(tags=[tag1, tag2], user=other_user)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_untag"],
                "bulk_execute": [""],
                "bulk_tag_string": [f"{tag1.name} {tag2.name}"],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_bulk_mark_as_read(self):
        bookmark1 = self.setup_bookmark(unread=True)
        bookmark2 = self.setup_bookmark(unread=True)
        bookmark3 = self.setup_bookmark(unread=True)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_read"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_can_only_bulk_mark_as_read_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(unread=True, user=other_user)
        bookmark2 = self.setup_bookmark(unread=True, user=other_user)
        bookmark3 = self.setup_bookmark(unread=True, user=other_user)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_read"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_bulk_mark_as_unread(self):
        bookmark1 = self.setup_bookmark(unread=False)
        bookmark2 = self.setup_bookmark(unread=False)
        bookmark3 = self.setup_bookmark(unread=False)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_unread"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_can_only_bulk_mark_as_unread_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(unread=False, user=other_user)
        bookmark2 = self.setup_bookmark(unread=False, user=other_user)
        bookmark3 = self.setup_bookmark(unread=False, user=other_user)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_unread"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_bulk_share(self):
        bookmark1 = self.setup_bookmark(shared=False)
        bookmark2 = self.setup_bookmark(shared=False)
        bookmark3 = self.setup_bookmark(shared=False)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_share"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_can_only_bulk_share_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(shared=False, user=other_user)
        bookmark2 = self.setup_bookmark(shared=False, user=other_user)
        bookmark3 = self.setup_bookmark(shared=False, user=other_user)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_share"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_bulk_unshare(self):
        bookmark1 = self.setup_bookmark(shared=True)
        bookmark2 = self.setup_bookmark(shared=True)
        bookmark3 = self.setup_bookmark(shared=True)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_unshare"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_can_only_bulk_unshare_own_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(shared=True, user=other_user)
        bookmark2 = self.setup_bookmark(shared=True, user=other_user)
        bookmark3 = self.setup_bookmark(shared=True, user=other_user)

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_unshare"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_bulk_select_across(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_archive"],
                "bulk_execute": [""],
                "bulk_select_across": ["on"],
            },
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_bulk_select_across_ignores_page(self):
        self.setup_numbered_bookmarks(100)

        self.client.post(
            reverse("bookmarks:index.action") + "?page=2",
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bulk_select_across": ["on"],
            },
        )

        self.assertEqual(0, Bookmark.objects.count())

    def setup_bulk_edit_scope_test_data(self):
        # create a number of bookmarks with different states / visibility
        self.setup_numbered_bookmarks(3, with_tags=True)
        self.setup_numbered_bookmarks(3, with_tags=True, archived=True)
        self.setup_numbered_bookmarks(
            3,
            shared=True,
            prefix="Joe's Bookmark",
            user=self.setup_user(enable_sharing=True),
        )

    def test_index_action_bulk_select_across_only_affects_active_bookmarks(self):
        self.setup_bulk_edit_scope_test_data()

        self.assertIsNotNone(Bookmark.objects.filter(title="Bookmark 1").first())
        self.assertIsNotNone(Bookmark.objects.filter(title="Bookmark 2").first())
        self.assertIsNotNone(Bookmark.objects.filter(title="Bookmark 3").first())

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bulk_select_across": ["on"],
            },
        )

        self.assertEqual(6, Bookmark.objects.count())
        self.assertIsNone(Bookmark.objects.filter(title="Bookmark 1").first())
        self.assertIsNone(Bookmark.objects.filter(title="Bookmark 2").first())
        self.assertIsNone(Bookmark.objects.filter(title="Bookmark 3").first())

    def test_index_action_bulk_select_across_respects_query(self):
        self.setup_numbered_bookmarks(3, prefix="foo")
        self.setup_numbered_bookmarks(3, prefix="bar")

        self.assertEqual(3, Bookmark.objects.filter(title__startswith="foo").count())

        self.client.post(
            reverse("bookmarks:index.action") + "?q=foo",
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bulk_select_across": ["on"],
            },
        )

        self.assertEqual(0, Bookmark.objects.filter(title__startswith="foo").count())
        self.assertEqual(3, Bookmark.objects.filter(title__startswith="bar").count())

    def test_archived_action_bulk_select_across_only_affects_archived_bookmarks(self):
        self.setup_bulk_edit_scope_test_data()

        self.assertIsNotNone(
            Bookmark.objects.filter(title="Archived Bookmark 1").first()
        )
        self.assertIsNotNone(
            Bookmark.objects.filter(title="Archived Bookmark 2").first()
        )
        self.assertIsNotNone(
            Bookmark.objects.filter(title="Archived Bookmark 3").first()
        )

        self.client.post(
            reverse("bookmarks:archived.action"),
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bulk_select_across": ["on"],
            },
        )

        self.assertEqual(6, Bookmark.objects.count())
        self.assertIsNone(Bookmark.objects.filter(title="Archived Bookmark 1").first())
        self.assertIsNone(Bookmark.objects.filter(title="Archived Bookmark 2").first())
        self.assertIsNone(Bookmark.objects.filter(title="Archived Bookmark 3").first())

    def test_archived_action_bulk_select_across_respects_query(self):
        self.setup_numbered_bookmarks(3, prefix="foo", archived=True)
        self.setup_numbered_bookmarks(3, prefix="bar", archived=True)

        self.assertEqual(3, Bookmark.objects.filter(title__startswith="foo").count())

        self.client.post(
            reverse("bookmarks:archived.action") + "?q=foo",
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bulk_select_across": ["on"],
            },
        )

        self.assertEqual(0, Bookmark.objects.filter(title__startswith="foo").count())
        self.assertEqual(3, Bookmark.objects.filter(title__startswith="bar").count())

    def test_shared_action_bulk_select_across_not_supported(self):
        self.setup_bulk_edit_scope_test_data()

        response = self.client.post(
            reverse("bookmarks:shared.action"),
            {
                "bulk_action": ["bulk_delete"],
                "bulk_execute": [""],
                "bulk_select_across": ["on"],
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_handles_empty_bookmark_id(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        response = self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_archive"],
                "bulk_execute": [""],
            },
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bulk_action": ["bulk_archive"],
                "bulk_execute": [""],
                "bookmark_id": [],
            },
        )
        self.assertEqual(response.status_code, 302)

        self.assertBookmarksAreUnmodified([bookmark1, bookmark2, bookmark3])

    def test_empty_action_does_not_modify_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(
            reverse("bookmarks:index.action"),
            {
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                    str(bookmark3.id),
                ],
            },
        )

        self.assertBookmarksAreUnmodified([bookmark1, bookmark2, bookmark3])

    def test_index_action_redirects_to_index_with_query_params(self):
        url = reverse("bookmarks:index.action") + "?q=foo&page=2"
        redirect_url = reverse("bookmarks:index") + "?q=foo&page=2"
        response = self.client.post(url)

        self.assertRedirects(response, redirect_url)

    def test_archived_action_redirects_to_archived_with_query_params(self):
        url = reverse("bookmarks:archived.action") + "?q=foo&page=2"
        redirect_url = reverse("bookmarks:archived") + "?q=foo&page=2"
        response = self.client.post(url)

        self.assertRedirects(response, redirect_url)

    def test_shared_action_redirects_to_shared_with_query_params(self):
        url = reverse("bookmarks:shared.action") + "?q=foo&page=2"
        redirect_url = reverse("bookmarks:shared") + "?q=foo&page=2"
        response = self.client.post(url)

        self.assertRedirects(response, redirect_url)

    def bookmark_update_fixture(self):
        user = self.get_or_create_test_user()
        profile = user.profile
        profile.enable_sharing = True
        profile.save()

        return {
            "active": self.setup_numbered_bookmarks(3),
            "archived": self.setup_numbered_bookmarks(3, archived=True),
            "shared": self.setup_numbered_bookmarks(3, shared=True),
        }

    def assertBookmarkUpdateResponse(self, response: HttpResponse):
        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8")
        soup = self.make_soup(html)

        # bookmark list update
        self.assertIsNotNone(
            soup.select_one(
                "turbo-stream[action='update'][target='bookmark-list-container']"
            )
        )

        # tag cloud update
        self.assertIsNotNone(
            soup.select_one(
                "turbo-stream[action='update'][target='tag-cloud-container']"
            )
        )

        # update event
        self.assertInHTML(
            """
            <script>
                document.dispatchEvent(new CustomEvent('bookmark-list-updated'));
            </script>
            """,
            html,
        )

    def test_index_action_with_turbo_returns_bookmark_update(self):
        fixture = self.bookmark_update_fixture()
        response = self.client.post(
            reverse("bookmarks:index.action"),
            HTTP_ACCEPT="text/vnd.turbo-stream.html",
        )

        visible_tags = self.get_tags_from_bookmarks(
            fixture["active"] + fixture["shared"]
        )
        invisible_tags = self.get_tags_from_bookmarks(fixture["archived"])

        self.assertBookmarkUpdateResponse(response)
        self.assertVisibleBookmarks(response, fixture["active"] + fixture["shared"])
        self.assertInvisibleBookmarks(response, fixture["archived"])
        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_archived_action_with_turbo_returns_bookmark_update(self):
        fixture = self.bookmark_update_fixture()
        response = self.client.post(
            reverse("bookmarks:archived.action"),
            HTTP_ACCEPT="text/vnd.turbo-stream.html",
        )

        visible_tags = self.get_tags_from_bookmarks(fixture["archived"])
        invisible_tags = self.get_tags_from_bookmarks(
            fixture["active"] + fixture["shared"]
        )

        self.assertBookmarkUpdateResponse(response)
        self.assertVisibleBookmarks(response, fixture["archived"])
        self.assertInvisibleBookmarks(response, fixture["active"] + fixture["shared"])
        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_shared_action_with_turbo_returns_bookmark_update(self):
        fixture = self.bookmark_update_fixture()
        response = self.client.post(
            reverse("bookmarks:shared.action"),
            HTTP_ACCEPT="text/vnd.turbo-stream.html",
        )

        visible_tags = self.get_tags_from_bookmarks(fixture["shared"])
        invisible_tags = self.get_tags_from_bookmarks(
            fixture["active"] + fixture["archived"]
        )

        self.assertBookmarkUpdateResponse(response)
        self.assertVisibleBookmarks(response, fixture["shared"])
        self.assertInvisibleBookmarks(response, fixture["active"] + fixture["archived"])
        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)
