from django.test import TestCase

from bookmarks.models import Bookmark


class BookmarkTestCase(TestCase):

    def test_bookmark_resolved_title(self):
        bookmark = Bookmark(
            title="Custom title",
            url="https://example.com",
        )
        self.assertEqual(bookmark.resolved_title, "Custom title")

        bookmark = Bookmark(title="", url="https://example.com")
        self.assertEqual(bookmark.resolved_title, "https://example.com")
