from typing import List

from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase


class BookmarkPagePartialUpdatesE2ETestCase(LinkdingE2ETestCase):
    def setup_fixture(self):
        # create a number of bookmarks with different states / visibility to
        # verify correct data is loaded on update
        self.setup_numbered_bookmarks(3, with_tags=True)
        self.setup_numbered_bookmarks(3, with_tags=True, archived=True)
        self.setup_numbered_bookmarks(3, with_tags=True, shared=True)

    def assertVisibleBookmarks(self, titles: List[str]):
        bookmark_tags = self.page.locator('ld-bookmark-item')
        expect(bookmark_tags).to_have_count(len(titles))

        for title in titles:
            matching_tag = bookmark_tags.filter(has_text=title)
            expect(matching_tag).to_be_visible()

    def assertVisibleTags(self, titles: List[str]):
        tag_tags = self.page.locator('.tag-cloud .unselected-tags a')
        expect(tag_tags).to_have_count(len(titles))

        for title in titles:
            matching_tag = tag_tags.filter(has_text=title)
            expect(matching_tag).to_be_visible()

    def test_partial_update_on_archive(self):
        self.setup_fixture()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:index'), p)

            self.locate_bookmark('Bookmark 2').get_by_text('Archive').click()

            self.assertVisibleBookmarks(['Bookmark 1', 'Bookmark 3'])
            self.assertVisibleTags(['Tag 1', 'Tag 3'])
            self.assertReloads(0)

    def test_partial_update_on_delete(self):
        self.setup_fixture()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:index'), p)

            self.locate_bookmark('Bookmark 2').get_by_text('Remove').click()
            self.locate_bookmark('Bookmark 2').get_by_text('Confirm').click()

            self.assertVisibleBookmarks(['Bookmark 1', 'Bookmark 3'])
            self.assertVisibleTags(['Tag 1', 'Tag 3'])
            self.assertReloads(0)

    def test_partial_update_on_mark_as_read(self):
        self.setup_fixture()
        bookmark2 = self.get_numbered_bookmark('Bookmark 2')
        bookmark2.unread = True
        bookmark2.save()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:index'), p)

            expect(self.locate_bookmark('Bookmark 2').get_by_text('Bookmark 2')).to_have_class('text-italic')
            self.locate_bookmark('Bookmark 2').get_by_text('Mark as read').click()

            expect(self.locate_bookmark('Bookmark 2').get_by_text('Bookmark 2')).not_to_have_class('text-italic')
            self.assertReloads(0)

    def test_partial_update_on_bulk_archive(self):
        self.setup_fixture()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:index'), p)

            self.locate_bulk_edit_toggle().click()
            self.locate_bookmark('Bookmark 2').locator('ld-bulk-edit-checkbox label').click()
            self.locate_bulk_edit_bar().get_by_text('Archive').click()
            self.locate_bulk_edit_bar().get_by_text('Confirm').click()

            self.assertVisibleBookmarks(['Bookmark 1', 'Bookmark 3'])
            self.assertVisibleTags(['Tag 1', 'Tag 3'])
            self.assertReloads(0)

    def test_partial_update_on_bulk_delete(self):
        self.setup_fixture()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:index'), p)

            self.locate_bulk_edit_toggle().click()
            self.locate_bookmark('Bookmark 2').locator('ld-bulk-edit-checkbox label').click()
            self.locate_bulk_edit_bar().get_by_text('Delete').click()
            self.locate_bulk_edit_bar().get_by_text('Confirm').click()

            self.assertVisibleBookmarks(['Bookmark 1', 'Bookmark 3'])
            self.assertVisibleTags(['Tag 1', 'Tag 3'])
            self.assertReloads(0)

    def test_partial_update_respects_query(self):
        self.setup_numbered_bookmarks(5, prefix='foo')
        self.setup_numbered_bookmarks(5, prefix='bar')

        with sync_playwright() as p:
            url = reverse('bookmarks:index') + '?q=foo'
            self.open(url, p)

            self.assertVisibleBookmarks(['foo 1', 'foo 2', 'foo 3', 'foo 4', 'foo 5'])

            self.locate_bookmark('foo 2').get_by_text('Archive').click()
            self.assertVisibleBookmarks(['foo 1', 'foo 3', 'foo 4', 'foo 5'])

    def test_partial_update_respects_page(self):
        # add a suffix, otherwise 'foo 1' also matches 'foo 10'
        self.setup_numbered_bookmarks(50, prefix='foo', suffix='-')

        with sync_playwright() as p:
            url = reverse('bookmarks:index') + '?q=foo&page=2'
            self.open(url, p)

            # with descending sort, page two has 'foo 1' to 'foo 20'
            expected_titles = [f'foo {i}-' for i in range(1, 21)]
            self.assertVisibleBookmarks(expected_titles)

            self.locate_bookmark('foo 20-').get_by_text('Archive').click()

            expected_titles = [f'foo {i}-' for i in range(1, 20)]
            self.assertVisibleBookmarks(expected_titles)
