from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class BookmarkItemE2ETestCase(LinkdingE2ETestCase):
    def test_update_preview_on_filter_changes(self):
        group1 = self.setup_numbered_bookmarks(3, prefix="foo")
        group2 = self.setup_numbered_bookmarks(3, prefix="bar")

        # shows all bookmarks initially
        page = self.open(reverse("linkding:bundles.new"))

        expect(
            page.get_by_text("Found 6 bookmarks matching this bundle")
        ).to_be_visible()
        self.assertVisibleBookmarks(group1 + group2)

        # filter by group1
        search = page.get_by_label("Search")
        search.fill("foo")

        expect(
            page.get_by_text("Found 3 bookmarks matching this bundle")
        ).to_be_visible()
        self.assertVisibleBookmarks(group1)

        # filter by group2
        search.fill("bar")

        expect(
            page.get_by_text("Found 3 bookmarks matching this bundle")
        ).to_be_visible()
        self.assertVisibleBookmarks(group2)

        # filter by invalid group
        search.fill("invalid")

        expect(
            page.get_by_text("No bookmarks match the current bundle")
        ).to_be_visible()
        self.assertVisibleBookmarks([])

    def assertVisibleBookmarks(self, bookmarks):
        self.assertEqual(len(bookmarks), self.count_bookmarks())

        for bookmark in bookmarks:
            expect(self.locate_bookmark(bookmark.title)).to_be_visible()
