from django.contrib.auth import get_user_model
from django.test import TestCase

from bookmarks import queries
from bookmarks.tests.helpers import BookmarkFactoryMixin

User = get_user_model()


class QueriesTestCase(TestCase, BookmarkFactoryMixin):

    def test_query_bookmarks_should_not_return_archived_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)

        query = queries.query_bookmarks(self.get_or_create_test_user(), '')

        self.assertCountEqual([bookmark1, bookmark2], list(query))

    def test_query_archived_bookmarks_should_not_return_unarchived_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        query = queries.query_archived_bookmarks(self.get_or_create_test_user(), '')

        self.assertCountEqual([bookmark1, bookmark2], list(query))

    def test_query_bookmark_tags_should_return_tags_for_unarchived_bookmarks_only(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True, tags=[tag2])

        query = queries.query_bookmark_tags(self.get_or_create_test_user(), '')

        self.assertCountEqual([tag1], list(query))

    def test_query_bookmark_tags_should_return_distinct_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmark_tags(self.get_or_create_test_user(), '')

        self.assertCountEqual([tag], list(query))

    def test_query_archived_bookmark_tags_should_return_tags_for_archived_bookmarks_only(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True, tags=[tag2])

        query = queries.query_archived_bookmark_tags(self.get_or_create_test_user(), '')

        self.assertCountEqual([tag2], list(query))

    def test_query_archived_bookmark_tags_should_return_distinct_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmark_tags(self.get_or_create_test_user(), '')

        self.assertCountEqual([tag], list(query))
