from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.utils.crypto import get_random_string
from bookmarks.models import Bookmark, Tag
from bookmarks import queries

User = get_user_model()


class QueriesTestCase(TestCase):

    def setUp(self) -> None:
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')

    def setup_bookmark(self, is_archived: bool = False, tags: [Tag] = []):
        unique_id = get_random_string(length=32)
        bookmark = Bookmark(
            url='https://example.com/' + unique_id,
            date_added=timezone.now(),
            date_modified=timezone.now(),
            owner=self.user,
            is_archived=is_archived
        )
        bookmark.save()
        for tag in tags:
            bookmark.tags.add(tag)
        bookmark.save()
        return bookmark

    def setup_tag(self):
        name = get_random_string(length=32)
        tag = Tag(name=name, date_added=timezone.now(), owner=self.user)
        tag.save()
        return tag

    def test_query_bookmarks_should_not_return_archived_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)

        query = queries.query_bookmarks(self.user, '')

        self.assertCountEqual([bookmark1, bookmark2], list(query))

    def test_query_archived_bookmarks_should_not_return_unarchived_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        query = queries.query_archived_bookmarks(self.user, '')

        self.assertCountEqual([bookmark1, bookmark2], list(query))

    def test_query_bookmark_tags_should_return_tags_for_unarchived_bookmarks_only(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True, tags=[tag2])

        query = queries.query_bookmark_tags(self.user, '')

        self.assertCountEqual([tag1], list(query))

    def test_query_bookmark_tags_should_return_distinct_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmark_tags(self.user, '')

        self.assertCountEqual([tag], list(query))

    def test_query_archived_bookmark_tags_should_return_tags_for_archived_bookmarks_only(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True, tags=[tag2])

        query = queries.query_archived_bookmark_tags(self.user, '')

        self.assertCountEqual([tag2], list(query))

    def test_query_archived_bookmark_tags_should_return_distinct_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmark_tags(self.user, '')

        self.assertCountEqual([tag], list(query))
