from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bookmarks.models import Bookmark
from bookmarks.services.bookmarks import archive_bookmark, unarchive_bookmark

User = get_user_model()


class BookmarkServiceTestCase(TestCase):

    def setUp(self) -> None:
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')

    def test_archive(self):
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

    def test_unarchive(self):
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
