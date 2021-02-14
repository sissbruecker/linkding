from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.utils.crypto import get_random_string
from bookmarks.models import Bookmark
from bookmarks.queries import query_bookmarks, query_archived_bookmarks

User = get_user_model()


class QueriesTestCase(TestCase):

    def setUp(self) -> None:
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')

    def setup_bookmark(self, is_archived: bool = False):
        unique_id = get_random_string(length=32)
        bookmark = Bookmark(
            url='https://example.com/' + unique_id,
            date_added=timezone.now(),
            date_modified=timezone.now(),
            owner=self.user,
            is_archived=is_archived
        )
        bookmark.save()
        return bookmark

    def test_query_bookmarks_should_not_return_archived_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)

        query = query_bookmarks(self.user, '')

        self.assertCountEqual([bookmark1, bookmark2], list(query))

    def test_query_archived_bookmarks_should_not_return_unarchived_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        query = query_archived_bookmarks(self.user, '')

        self.assertCountEqual([bookmark1, bookmark2], list(query))
