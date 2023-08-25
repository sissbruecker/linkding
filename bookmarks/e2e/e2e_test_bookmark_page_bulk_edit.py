from django.urls import reverse
from playwright.sync_api import sync_playwright

from bookmarks.e2e.helpers import LinkdingE2ETestCase
from bookmarks.models import Bookmark


class BookmarkPagePartialUpdatesE2ETestCase(LinkdingE2ETestCase):
    def setup_test_data(self):
        self.setup_numbered_bookmarks(50)
        self.setup_numbered_bookmarks(50, archived=True)
        self.setup_numbered_bookmarks(50, prefix='foo')
        self.setup_numbered_bookmarks(50, archived=True, prefix='foo')

        self.assertEqual(50, Bookmark.objects.filter(is_archived=False, title__startswith='Bookmark').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=True, title__startswith='Archived Bookmark').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=False, title__startswith='foo').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=True, title__startswith='foo').count())

    def test_active_bookmarks_bulk_select_across(self):
        self.setup_test_data()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:index'), p)

            self.locate_bulk_edit_toggle().click()
            self.locate_bulk_edit_select_all().click()
            self.locate_bulk_edit_select_across().click()

            self.select_bulk_action('Delete')
            self.locate_bulk_edit_bar().get_by_text('Execute').click()
            self.locate_bulk_edit_bar().get_by_text('Confirm').click()

        self.assertEqual(0, Bookmark.objects.filter(is_archived=False, title__startswith='Bookmark').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=True, title__startswith='Archived Bookmark').count())
        self.assertEqual(0, Bookmark.objects.filter(is_archived=False, title__startswith='foo').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=True, title__startswith='foo').count())

    def test_archived_bookmarks_bulk_select_across(self):
        self.setup_test_data()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:archived'), p)

            self.locate_bulk_edit_toggle().click()
            self.locate_bulk_edit_select_all().click()
            self.locate_bulk_edit_select_across().click()

            self.select_bulk_action('Delete')
            self.locate_bulk_edit_bar().get_by_text('Execute').click()
            self.locate_bulk_edit_bar().get_by_text('Confirm').click()

        self.assertEqual(50, Bookmark.objects.filter(is_archived=False, title__startswith='Bookmark').count())
        self.assertEqual(0, Bookmark.objects.filter(is_archived=True, title__startswith='Archived Bookmark').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=False, title__startswith='foo').count())
        self.assertEqual(0, Bookmark.objects.filter(is_archived=True, title__startswith='foo').count())

    def test_active_bookmarks_bulk_select_across_respects_query(self):
        self.setup_test_data()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:index') + '?q=foo', p)

            self.locate_bulk_edit_toggle().click()
            self.locate_bulk_edit_select_all().click()
            self.locate_bulk_edit_select_across().click()

            self.select_bulk_action('Delete')
            self.locate_bulk_edit_bar().get_by_text('Execute').click()
            self.locate_bulk_edit_bar().get_by_text('Confirm').click()

        self.assertEqual(50, Bookmark.objects.filter(is_archived=False, title__startswith='Bookmark').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=True, title__startswith='Archived Bookmark').count())
        self.assertEqual(0, Bookmark.objects.filter(is_archived=False, title__startswith='foo').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=True, title__startswith='foo').count())

    def test_archived_bookmarks_bulk_select_across_respects_query(self):
        self.setup_test_data()

        with sync_playwright() as p:
            self.open(reverse('bookmarks:archived') + '?q=foo', p)

            self.locate_bulk_edit_toggle().click()
            self.locate_bulk_edit_select_all().click()
            self.locate_bulk_edit_select_across().click()

            self.select_bulk_action('Delete')
            self.locate_bulk_edit_bar().get_by_text('Execute').click()
            self.locate_bulk_edit_bar().get_by_text('Confirm').click()

        self.assertEqual(50, Bookmark.objects.filter(is_archived=False, title__startswith='Bookmark').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=True, title__startswith='Archived Bookmark').count())
        self.assertEqual(50, Bookmark.objects.filter(is_archived=False, title__startswith='foo').count())
        self.assertEqual(0, Bookmark.objects.filter(is_archived=True, title__startswith='foo').count())
