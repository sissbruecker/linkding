from django.test import TestCase

from bookmarks.models import Bookmark, Link


class BookmarkTestCase(TestCase):

    def test_bookmark_resolved_title(self):
        link = Link(website_title="Website title", url="https://example.com")
        link.save()
        bookmark = Bookmark(
            title="Custom title",
            link=link,
        )
        self.assertEqual(bookmark.resolved_title, "Custom title")

        bookmark = Bookmark(title="", link=link)
        self.assertEqual(bookmark.resolved_title, "Website title")

        link.website_title = ""
        link.save()
        bookmark = Bookmark(title="", link=link)
        self.assertEqual(bookmark.resolved_title, "https://example.com")
