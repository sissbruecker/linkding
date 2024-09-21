import os
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from bookmarks.models import Bookmark, BookmarkAsset, Tag
from bookmarks.services import tasks
from bookmarks.services import website_loader
from bookmarks.services.bookmarks import (
    create_bookmark,
    update_bookmark,
    archive_bookmark,
    archive_bookmarks,
    unarchive_bookmark,
    unarchive_bookmarks,
    delete_bookmarks,
    tag_bookmarks,
    untag_bookmarks,
    mark_bookmarks_as_read,
    mark_bookmarks_as_unread,
    share_bookmarks,
    unshare_bookmarks,
    upload_asset,
    enhance_with_website_metadata,
)
from bookmarks.tests.helpers import BookmarkFactoryMixin

User = get_user_model()


class BookmarkServiceTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        self.get_or_create_test_user()

    def test_create_should_not_update_website_metadata(self):
        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            bookmark_data = Bookmark(
                url="https://example.com",
                title="Initial Title",
                description="Initial description",
                unread=True,
                shared=True,
                is_archived=True,
            )
            created_bookmark = create_bookmark(
                bookmark_data, "", self.get_or_create_test_user()
            )

            created_bookmark.refresh_from_db()
            self.assertEqual("Initial Title", created_bookmark.title)
            self.assertEqual("Initial description", created_bookmark.description)
            mock_load_website_metadata.assert_not_called()

    def test_create_should_update_existing_bookmark_with_same_url(self):
        original_bookmark = self.setup_bookmark(
            url="https://example.com", unread=False, shared=False
        )
        bookmark_data = Bookmark(
            url="https://example.com",
            title="Updated Title",
            description="Updated description",
            notes="Updated notes",
            unread=True,
            shared=True,
            is_archived=True,
        )
        updated_bookmark = create_bookmark(
            bookmark_data, "", self.get_or_create_test_user()
        )

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(updated_bookmark.id, original_bookmark.id)
        self.assertEqual(updated_bookmark.title, bookmark_data.title)
        self.assertEqual(updated_bookmark.description, bookmark_data.description)
        self.assertEqual(updated_bookmark.notes, bookmark_data.notes)
        self.assertEqual(updated_bookmark.unread, bookmark_data.unread)
        self.assertEqual(updated_bookmark.shared, bookmark_data.shared)
        # Saving a duplicate bookmark should not modify archive flag - right?
        self.assertFalse(updated_bookmark.is_archived)

    def test_create_should_create_web_archive_snapshot(self):
        with patch.object(
            tasks, "create_web_archive_snapshot"
        ) as mock_create_web_archive_snapshot:
            bookmark_data = Bookmark(url="https://example.com")
            bookmark = create_bookmark(bookmark_data, "tag1,tag2", self.user)

            mock_create_web_archive_snapshot.assert_called_once_with(
                self.user, bookmark, False
            )

    def test_create_should_load_favicon(self):
        with patch.object(tasks, "load_favicon") as mock_load_favicon:
            bookmark_data = Bookmark(url="https://example.com")
            bookmark = create_bookmark(bookmark_data, "tag1,tag2", self.user)

            mock_load_favicon.assert_called_once_with(self.user, bookmark)

    def test_create_should_load_html_snapshot(self):
        with patch.object(tasks, "create_html_snapshot") as mock_create_html_snapshot:
            bookmark_data = Bookmark(url="https://example.com")
            bookmark = create_bookmark(bookmark_data, "tag1,tag2", self.user)

            mock_create_html_snapshot.assert_called_once_with(bookmark)

    def test_create_should_not_load_html_snapshot_when_setting_is_disabled(self):
        profile = self.get_or_create_test_user().profile
        profile.enable_automatic_html_snapshots = False
        profile.save()

        with patch.object(tasks, "create_html_snapshot") as mock_create_html_snapshot:
            bookmark_data = Bookmark(url="https://example.com")
            create_bookmark(bookmark_data, "tag1,tag2", self.user)

            mock_create_html_snapshot.assert_not_called()

    def test_create_should_add_tags_from_auto_tagging(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        profile = self.get_or_create_test_user().profile
        profile.auto_tagging_rules = f"example.com {tag2.name}"
        profile.save()

        bookmark_data = Bookmark(url="https://example.com")
        bookmark = create_bookmark(bookmark_data, tag1.name, self.user)

        self.assertCountEqual(bookmark.tags.all(), [tag1, tag2])

    def test_update_should_create_web_archive_snapshot_if_url_did_change(self):
        with patch.object(
            tasks, "create_web_archive_snapshot"
        ) as mock_create_web_archive_snapshot:
            bookmark = self.setup_bookmark()
            bookmark.url = "https://example.com/updated"
            update_bookmark(bookmark, "tag1,tag2", self.user)

            mock_create_web_archive_snapshot.assert_called_once_with(
                self.user, bookmark, True
            )

    def test_update_should_not_create_web_archive_snapshot_if_url_did_not_change(self):
        with patch.object(
            tasks, "create_web_archive_snapshot"
        ) as mock_create_web_archive_snapshot:
            bookmark = self.setup_bookmark()
            bookmark.title = "updated title"
            update_bookmark(bookmark, "tag1,tag2", self.user)

            mock_create_web_archive_snapshot.assert_not_called()

    def test_update_should_not_update_website_metadata(self):
        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            bookmark = self.setup_bookmark()
            bookmark.title = "updated title"
            update_bookmark(bookmark, "tag1,tag2", self.user)
            bookmark.refresh_from_db()

            self.assertEqual("updated title", bookmark.title)
            mock_load_website_metadata.assert_not_called()

    def test_update_should_not_update_website_metadata_if_url_did_change(self):
        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            bookmark = self.setup_bookmark(title="initial title")
            bookmark.url = "https://example.com/updated"
            update_bookmark(bookmark, "tag1,tag2", self.user)

            bookmark.refresh_from_db()
            self.assertEqual("initial title", bookmark.title)
            mock_load_website_metadata.assert_not_called()

    def test_update_should_update_favicon(self):
        with patch.object(tasks, "load_favicon") as mock_load_favicon:
            bookmark = self.setup_bookmark()
            bookmark.title = "updated title"
            update_bookmark(bookmark, "tag1,tag2", self.user)

            mock_load_favicon.assert_called_once_with(self.user, bookmark)

    def test_update_should_not_create_html_snapshot(self):
        with patch.object(tasks, "create_html_snapshot") as mock_create_html_snapshot:
            bookmark = self.setup_bookmark()
            bookmark.title = "updated title"
            update_bookmark(bookmark, "tag1,tag2", self.user)

            mock_create_html_snapshot.assert_not_called()

    def test_update_should_add_tags_from_auto_tagging(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        profile = self.get_or_create_test_user().profile
        profile.auto_tagging_rules = f"example.com {tag2.name}"
        profile.save()
        bookmark = self.setup_bookmark(url="https://example.com")

        update_bookmark(bookmark, tag1.name, self.user)

        self.assertCountEqual(bookmark.tags.all(), [tag1, tag2])

    def test_archive_bookmark(self):
        bookmark = Bookmark(
            url="https://example.com",
            date_added=timezone.now(),
            date_modified=timezone.now(),
            owner=self.user,
        )
        bookmark.save()

        self.assertFalse(bookmark.is_archived)

        archive_bookmark(bookmark)

        updated_bookmark = Bookmark.objects.get(id=bookmark.id)

        self.assertTrue(updated_bookmark.is_archived)

    def test_unarchive_bookmark(self):
        bookmark = Bookmark(
            url="https://example.com",
            date_added=timezone.now(),
            date_modified=timezone.now(),
            owner=self.user,
            is_archived=True,
        )
        bookmark.save()

        unarchive_bookmark(bookmark)

        updated_bookmark = Bookmark.objects.get(id=bookmark.id)

        self.assertFalse(updated_bookmark.is_archived)

    def test_archive_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        archive_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_archive_bookmarks_should_only_archive_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        archive_bookmarks([bookmark1.id, bookmark3.id], self.get_or_create_test_user())

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_archive_bookmarks_should_only_archive_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        inaccessible_bookmark = self.setup_bookmark(user=other_user)

        archive_bookmarks(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            self.get_or_create_test_user(),
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=inaccessible_bookmark.id).is_archived)

    def test_archive_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        archive_bookmarks(
            [str(bookmark1.id), bookmark2.id, str(bookmark3.id)],
            self.get_or_create_test_user(),
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_unarchive_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        unarchive_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_unarchive_bookmarks_should_only_unarchive_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        unarchive_bookmarks(
            [bookmark1.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_unarchive_bookmarks_should_only_unarchive_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        inaccessible_bookmark = self.setup_bookmark(is_archived=True, user=other_user)

        unarchive_bookmarks(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            self.get_or_create_test_user(),
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=inaccessible_bookmark.id).is_archived)

    def test_unarchive_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        unarchive_bookmarks(
            [str(bookmark1.id), bookmark2.id, str(bookmark3.id)],
            self.get_or_create_test_user(),
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_delete_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        delete_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertIsNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark3.id).first())

    def test_delete_bookmarks_should_only_delete_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        delete_bookmarks([bookmark1.id, bookmark3.id], self.get_or_create_test_user())

        self.assertIsNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNotNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark3.id).first())

    def test_delete_bookmarks_should_only_delete_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        inaccessible_bookmark = self.setup_bookmark(user=other_user)

        delete_bookmarks(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            self.get_or_create_test_user(),
        )

        self.assertIsNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNotNone(
            Bookmark.objects.filter(id=inaccessible_bookmark.id).first()
        )

    def test_delete_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        delete_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertIsNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark3.id).first())

    def test_tag_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        tag_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_tag_bookmarks_should_create_tags(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        tag_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id],
            "tag1,tag2",
            self.get_or_create_test_user(),
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertEqual(2, Tag.objects.count())

        tag1 = Tag.objects.filter(name="tag1").first()
        tag2 = Tag.objects.filter(name="tag2").first()

        self.assertIsNotNone(tag1)
        self.assertIsNotNone(tag2)

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_tag_bookmarks_should_handle_existing_relationships(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1])
        bookmark2 = self.setup_bookmark(tags=[tag1])
        bookmark3 = self.setup_bookmark(tags=[tag1])

        BookmarkToTagRelationShip = Bookmark.tags.through
        self.assertEqual(3, BookmarkToTagRelationShip.objects.count())

        tag_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])
        self.assertEqual(6, BookmarkToTagRelationShip.objects.count())

    def test_tag_bookmarks_should_only_tag_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        tag_bookmarks(
            [bookmark1.id, bookmark3.id],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_tag_bookmarks_should_only_tag_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        inaccessible_bookmark = self.setup_bookmark(user=other_user)
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        tag_bookmarks(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        inaccessible_bookmark.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(inaccessible_bookmark.tags.all(), [])

    def test_tag_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        tag_bookmarks(
            [str(bookmark1.id), bookmark2.id, str(bookmark3.id)],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_untag_bookmarks(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark3 = self.setup_bookmark(tags=[tag1, tag2])

        untag_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [])

    def test_untag_bookmarks_should_only_tag_specified_bookmarks(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark3 = self.setup_bookmark(tags=[tag1, tag2])

        untag_bookmarks(
            [bookmark1.id, bookmark3.id],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [])

    def test_untag_bookmarks_should_only_tag_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2])
        inaccessible_bookmark = self.setup_bookmark(user=other_user, tags=[tag1, tag2])

        untag_bookmarks(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        inaccessible_bookmark.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(inaccessible_bookmark.tags.all(), [tag1, tag2])

    def test_untag_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark3 = self.setup_bookmark(tags=[tag1, tag2])

        untag_bookmarks(
            [str(bookmark1.id), bookmark2.id, str(bookmark3.id)],
            f"{tag1.name},{tag2.name}",
            self.get_or_create_test_user(),
        )

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [])

    def test_mark_bookmarks_as_read(self):
        bookmark1 = self.setup_bookmark(unread=True)
        bookmark2 = self.setup_bookmark(unread=True)
        bookmark3 = self.setup_bookmark(unread=True)

        mark_bookmarks_as_read(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_mark_bookmarks_as_read_should_only_update_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark(unread=True)
        bookmark2 = self.setup_bookmark(unread=True)
        bookmark3 = self.setup_bookmark(unread=True)

        mark_bookmarks_as_read(
            [bookmark1.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_mark_bookmarks_as_read_should_only_update_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(unread=True)
        bookmark2 = self.setup_bookmark(unread=True)
        inaccessible_bookmark = self.setup_bookmark(unread=True, user=other_user)

        mark_bookmarks_as_read(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            self.get_or_create_test_user(),
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertTrue(Bookmark.objects.get(id=inaccessible_bookmark.id).unread)

    def test_mark_bookmarks_as_read_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark(unread=True)
        bookmark2 = self.setup_bookmark(unread=True)
        bookmark3 = self.setup_bookmark(unread=True)

        mark_bookmarks_as_read(
            [str(bookmark1.id), bookmark2.id, str(bookmark3.id)],
            self.get_or_create_test_user(),
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_mark_bookmarks_as_unread(self):
        bookmark1 = self.setup_bookmark(unread=False)
        bookmark2 = self.setup_bookmark(unread=False)
        bookmark3 = self.setup_bookmark(unread=False)

        mark_bookmarks_as_unread(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_mark_bookmarks_as_unread_should_only_update_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark(unread=False)
        bookmark2 = self.setup_bookmark(unread=False)
        bookmark3 = self.setup_bookmark(unread=False)

        mark_bookmarks_as_unread(
            [bookmark1.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_mark_bookmarks_as_unread_should_only_update_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(unread=False)
        bookmark2 = self.setup_bookmark(unread=False)
        inaccessible_bookmark = self.setup_bookmark(unread=False, user=other_user)

        mark_bookmarks_as_unread(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            self.get_or_create_test_user(),
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertFalse(Bookmark.objects.get(id=inaccessible_bookmark.id).unread)

    def test_mark_bookmarks_as_unread_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark(unread=False)
        bookmark2 = self.setup_bookmark(unread=False)
        bookmark3 = self.setup_bookmark(unread=False)

        mark_bookmarks_as_unread(
            [str(bookmark1.id), bookmark2.id, str(bookmark3.id)],
            self.get_or_create_test_user(),
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).unread)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).unread)

    def test_share_bookmarks(self):
        bookmark1 = self.setup_bookmark(shared=False)
        bookmark2 = self.setup_bookmark(shared=False)
        bookmark3 = self.setup_bookmark(shared=False)

        share_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_share_bookmarks_should_only_update_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark(shared=False)
        bookmark2 = self.setup_bookmark(shared=False)
        bookmark3 = self.setup_bookmark(shared=False)

        share_bookmarks([bookmark1.id, bookmark3.id], self.get_or_create_test_user())

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_share_bookmarks_should_only_update_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(shared=False)
        bookmark2 = self.setup_bookmark(shared=False)
        inaccessible_bookmark = self.setup_bookmark(shared=False, user=other_user)

        share_bookmarks(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            self.get_or_create_test_user(),
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertFalse(Bookmark.objects.get(id=inaccessible_bookmark.id).shared)

    def test_share_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark(shared=False)
        bookmark2 = self.setup_bookmark(shared=False)
        bookmark3 = self.setup_bookmark(shared=False)

        share_bookmarks(
            [str(bookmark1.id), bookmark2.id, str(bookmark3.id)],
            self.get_or_create_test_user(),
        )

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_unshare_bookmarks(self):
        bookmark1 = self.setup_bookmark(shared=True)
        bookmark2 = self.setup_bookmark(shared=True)
        bookmark3 = self.setup_bookmark(shared=True)

        unshare_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_unshare_bookmarks_should_only_update_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark(shared=True)
        bookmark2 = self.setup_bookmark(shared=True)
        bookmark3 = self.setup_bookmark(shared=True)

        unshare_bookmarks([bookmark1.id, bookmark3.id], self.get_or_create_test_user())

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_unshare_bookmarks_should_only_update_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        bookmark1 = self.setup_bookmark(shared=True)
        bookmark2 = self.setup_bookmark(shared=True)
        inaccessible_bookmark = self.setup_bookmark(shared=True, user=other_user)

        unshare_bookmarks(
            [bookmark1.id, bookmark2.id, inaccessible_bookmark.id],
            self.get_or_create_test_user(),
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertTrue(Bookmark.objects.get(id=inaccessible_bookmark.id).shared)

    def test_unshare_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark(shared=True)
        bookmark2 = self.setup_bookmark(shared=True)
        bookmark3 = self.setup_bookmark(shared=True)

        unshare_bookmarks(
            [str(bookmark1.id), bookmark2.id, str(bookmark3.id)],
            self.get_or_create_test_user(),
        )

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).shared)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).shared)

    def test_upload_asset_should_save_file(self):
        bookmark = self.setup_bookmark()
        with tempfile.TemporaryDirectory() as temp_assets:
            with override_settings(LD_ASSET_FOLDER=temp_assets):
                file_content = b"file content"
                upload_file = SimpleUploadedFile(
                    "test_file.txt", file_content, content_type="text/plain"
                )
                upload_asset(bookmark, upload_file)

                assets = bookmark.bookmarkasset_set.all()
                self.assertEqual(1, len(assets))

                asset = assets[0]
                self.assertEqual("test_file.txt", asset.display_name)
                self.assertEqual("text/plain", asset.content_type)
                self.assertEqual(upload_file.size, asset.file_size)
                self.assertEqual(BookmarkAsset.STATUS_COMPLETE, asset.status)
                self.assertTrue(asset.file.startswith("upload_"))
                self.assertTrue(asset.file.endswith(upload_file.name))

                # check file exists
                filepath = os.path.join(temp_assets, asset.file)
                self.assertTrue(os.path.exists(filepath))
                with open(filepath, "rb") as f:
                    self.assertEqual(file_content, f.read())

    def test_upload_asset_should_be_failed_if_saving_file_fails(self):
        bookmark = self.setup_bookmark()
        # Use an invalid path to force an error
        with override_settings(LD_ASSET_FOLDER="/non/existing/folder"):
            file_content = b"file content"
            upload_file = SimpleUploadedFile(
                "test_file.txt", file_content, content_type="text/plain"
            )
            upload_asset(bookmark, upload_file)

            assets = bookmark.bookmarkasset_set.all()
            self.assertEqual(1, len(assets))

            asset = assets[0]
            self.assertEqual("test_file.txt", asset.display_name)
            self.assertEqual("text/plain", asset.content_type)
            self.assertIsNone(asset.file_size)
            self.assertEqual(BookmarkAsset.STATUS_FAILURE, asset.status)
            self.assertEqual("", asset.file)

    def test_enhance_with_website_metadata(self):
        bookmark = self.setup_bookmark(url="https://example.com")
        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            mock_load_website_metadata.return_value = website_loader.WebsiteMetadata(
                url="https://example.com",
                title="Website title",
                description="Website description",
                preview_image=None,
            )

            # missing title and description
            bookmark.title = ""
            bookmark.description = ""
            bookmark.save()
            enhance_with_website_metadata(bookmark)
            bookmark.refresh_from_db()

            self.assertEqual("Website title", bookmark.title)
            self.assertEqual("Website description", bookmark.description)

            # missing title only
            bookmark.title = ""
            bookmark.description = "Initial description"
            bookmark.save()
            enhance_with_website_metadata(bookmark)
            bookmark.refresh_from_db()

            self.assertEqual("Website title", bookmark.title)
            self.assertEqual("Initial description", bookmark.description)

            # missing description only
            bookmark.title = "Initial title"
            bookmark.description = ""
            bookmark.save()
            enhance_with_website_metadata(bookmark)
            bookmark.refresh_from_db()

            self.assertEqual("Initial title", bookmark.title)
            self.assertEqual("Website description", bookmark.description)

            # metadata returns None
            mock_load_website_metadata.return_value = website_loader.WebsiteMetadata(
                url="https://example.com",
                title=None,
                description=None,
                preview_image=None,
            )
            bookmark.title = ""
            bookmark.description = ""
            bookmark.save()
            enhance_with_website_metadata(bookmark)
            bookmark.refresh_from_db()

            self.assertEqual("", bookmark.title)
            self.assertEqual("", bookmark.description)
