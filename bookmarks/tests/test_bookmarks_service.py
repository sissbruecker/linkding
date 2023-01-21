from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bookmarks.models import Bookmark, Tag
from bookmarks.services import tasks
from bookmarks.services import website_loader
from bookmarks.services.bookmarks import create_bookmark, update_bookmark, archive_bookmark, archive_bookmarks, \
    unarchive_bookmark, unarchive_bookmarks, delete_bookmarks, tag_bookmarks, untag_bookmarks
from bookmarks.services.website_loader import WebsiteMetadata
from bookmarks.tests.helpers import BookmarkFactoryMixin

User = get_user_model()


class BookmarkServiceTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        self.get_or_create_test_user()

    def test_create_should_update_website_metadata(self):
        with patch.object(website_loader, 'load_website_metadata') as mock_load_website_metadata:
            expected_metadata = WebsiteMetadata(
                'https://example.com',
                'Website title',
                'Website description'
            )
            mock_load_website_metadata.return_value = expected_metadata

            bookmark_data = Bookmark(url='https://example.com',
                                     title='Updated Title',
                                     description='Updated description',
                                     unread=True,
                                     shared=True,
                                     is_archived=True)
            created_bookmark = create_bookmark(bookmark_data, '', self.get_or_create_test_user())

            created_bookmark.refresh_from_db()
            self.assertEqual(expected_metadata.title, created_bookmark.website_title)
            self.assertEqual(expected_metadata.description, created_bookmark.website_description)

    def test_create_should_update_existing_bookmark_with_same_url(self):
        original_bookmark = self.setup_bookmark(url='https://example.com', unread=False, shared=False)
        bookmark_data = Bookmark(url='https://example.com',
                                 title='Updated Title',
                                 description='Updated description',
                                 unread=True,
                                 shared=True,
                                 is_archived=True)
        updated_bookmark = create_bookmark(bookmark_data, '', self.get_or_create_test_user())

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(updated_bookmark.id, original_bookmark.id)
        self.assertEqual(updated_bookmark.title, bookmark_data.title)
        self.assertEqual(updated_bookmark.description, bookmark_data.description)
        self.assertEqual(updated_bookmark.unread, bookmark_data.unread)
        self.assertEqual(updated_bookmark.shared, bookmark_data.shared)
        # Saving a duplicate bookmark should not modify archive flag - right?
        self.assertFalse(updated_bookmark.is_archived)

    def test_create_should_create_web_archive_snapshot(self):
        with patch.object(tasks, 'create_web_archive_snapshot') as mock_create_web_archive_snapshot:
            bookmark_data = Bookmark(url='https://example.com')
            bookmark = create_bookmark(bookmark_data, 'tag1,tag2', self.user)

            mock_create_web_archive_snapshot.assert_called_once_with(self.user, bookmark, False)

    def test_create_should_load_favicon(self):
        with patch.object(tasks, 'load_favicon') as mock_load_favicon:
            bookmark_data = Bookmark(url='https://example.com')
            bookmark = create_bookmark(bookmark_data, 'tag1,tag2', self.user)

            mock_load_favicon.assert_called_once_with(self.user, bookmark)

    def test_update_should_create_web_archive_snapshot_if_url_did_change(self):
        with patch.object(tasks, 'create_web_archive_snapshot') as mock_create_web_archive_snapshot:
            bookmark = self.setup_bookmark()
            bookmark.url = 'https://example.com/updated'
            update_bookmark(bookmark, 'tag1,tag2', self.user)

            mock_create_web_archive_snapshot.assert_called_once_with(self.user, bookmark, True)

    def test_update_should_not_create_web_archive_snapshot_if_url_did_not_change(self):
        with patch.object(tasks, 'create_web_archive_snapshot') as mock_create_web_archive_snapshot:
            bookmark = self.setup_bookmark()
            bookmark.title = 'updated title'
            update_bookmark(bookmark, 'tag1,tag2', self.user)

            mock_create_web_archive_snapshot.assert_not_called()

    def test_update_should_update_website_metadata_if_url_did_change(self):
        with patch.object(website_loader, 'load_website_metadata') as mock_load_website_metadata:
            expected_metadata = WebsiteMetadata(
                'https://example.com/updated',
                'Updated website title',
                'Updated website description'
            )
            mock_load_website_metadata.return_value = expected_metadata

            bookmark = self.setup_bookmark()
            bookmark.url = 'https://example.com/updated'
            update_bookmark(bookmark, 'tag1,tag2', self.user)

            bookmark.refresh_from_db()
            mock_load_website_metadata.assert_called_once()
            self.assertEqual(expected_metadata.title, bookmark.website_title)
            self.assertEqual(expected_metadata.description, bookmark.website_description)

    def test_update_should_not_update_website_metadata_if_url_did_not_change(self):
        with patch.object(website_loader, 'load_website_metadata') as mock_load_website_metadata:
            bookmark = self.setup_bookmark()
            bookmark.title = 'updated title'
            update_bookmark(bookmark, 'tag1,tag2', self.user)

            mock_load_website_metadata.assert_not_called()

    def test_update_should_update_favicon(self):
        with patch.object(tasks, 'load_favicon') as mock_load_favicon:
            bookmark = self.setup_bookmark()
            bookmark.title = 'updated title'
            update_bookmark(bookmark, 'tag1,tag2', self.user)

            mock_load_favicon.assert_called_once_with(self.user, bookmark)

    def test_archive_bookmark(self):
        bookmark = Bookmark(
            url='https://example.com',
            date_added=timezone.now(),
            date_modified=timezone.now(),
            owner=self.user
        )
        bookmark.save()

        self.assertFalse(bookmark.is_archived)

        archive_bookmark(bookmark)

        updated_bookmark = Bookmark.objects.get(id=bookmark.id)

        self.assertTrue(updated_bookmark.is_archived)

    def test_unarchive_bookmark(self):
        bookmark = Bookmark(
            url='https://example.com',
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

        archive_bookmarks([bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user())

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
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        inaccessible_bookmark = self.setup_bookmark(user=other_user)

        archive_bookmarks([bookmark1.id, bookmark2.id, inaccessible_bookmark.id], self.get_or_create_test_user())

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=inaccessible_bookmark.id).is_archived)

    def test_archive_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        archive_bookmarks([str(bookmark1.id), bookmark2.id, str(bookmark3.id)], self.get_or_create_test_user())

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_unarchive_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        unarchive_bookmarks([bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user())

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_unarchive_bookmarks_should_only_unarchive_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        unarchive_bookmarks([bookmark1.id, bookmark3.id], self.get_or_create_test_user())

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_unarchive_bookmarks_should_only_unarchive_user_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        inaccessible_bookmark = self.setup_bookmark(is_archived=True, user=other_user)

        unarchive_bookmarks([bookmark1.id, bookmark2.id, inaccessible_bookmark.id], self.get_or_create_test_user())

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=inaccessible_bookmark.id).is_archived)

    def test_unarchive_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        unarchive_bookmarks([str(bookmark1.id), bookmark2.id, str(bookmark3.id)], self.get_or_create_test_user())

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_delete_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        delete_bookmarks([bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user())

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
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        inaccessible_bookmark = self.setup_bookmark(user=other_user)

        delete_bookmarks([bookmark1.id, bookmark2.id, inaccessible_bookmark.id], self.get_or_create_test_user())

        self.assertIsNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNotNone(Bookmark.objects.filter(id=inaccessible_bookmark.id).first())

    def test_delete_bookmarks_should_accept_mix_of_int_and_string_ids(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        delete_bookmarks([bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user())

        self.assertIsNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark3.id).first())

    def test_tag_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        tag_bookmarks([bookmark1.id, bookmark2.id, bookmark3.id], f'{tag1.name},{tag2.name}',
                      self.get_or_create_test_user())

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

        tag_bookmarks([bookmark1.id, bookmark2.id, bookmark3.id], 'tag1,tag2', self.get_or_create_test_user())

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertEqual(2, Tag.objects.count())

        tag1 = Tag.objects.filter(name='tag1').first()
        tag2 = Tag.objects.filter(name='tag2').first()

        self.assertIsNotNone(tag1)
        self.assertIsNotNone(tag2)

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_tag_bookmarks_should_only_tag_specified_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        tag_bookmarks([bookmark1.id, bookmark3.id], f'{tag1.name},{tag2.name}', self.get_or_create_test_user())

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_tag_bookmarks_should_only_tag_user_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        inaccessible_bookmark = self.setup_bookmark(user=other_user)
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        tag_bookmarks([bookmark1.id, bookmark2.id, inaccessible_bookmark.id], f'{tag1.name},{tag2.name}',
                      self.get_or_create_test_user())

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

        tag_bookmarks([str(bookmark1.id), bookmark2.id, str(bookmark3.id)], f'{tag1.name},{tag2.name}',
                      self.get_or_create_test_user())

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_untag_bookmarks(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark3 = self.setup_bookmark(tags=[tag1, tag2])

        untag_bookmarks([bookmark1.id, bookmark2.id, bookmark3.id], f'{tag1.name},{tag2.name}',
                        self.get_or_create_test_user())

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

        untag_bookmarks([bookmark1.id, bookmark3.id], f'{tag1.name},{tag2.name}', self.get_or_create_test_user())

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [])

    def test_untag_bookmarks_should_only_tag_user_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2])
        inaccessible_bookmark = self.setup_bookmark(user=other_user, tags=[tag1, tag2])

        untag_bookmarks([bookmark1.id, bookmark2.id, inaccessible_bookmark.id], f'{tag1.name},{tag2.name}',
                        self.get_or_create_test_user())

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

        untag_bookmarks([str(bookmark1.id), bookmark2.id, str(bookmark3.id)], f'{tag1.name},{tag2.name}',
                        self.get_or_create_test_user())

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [])
