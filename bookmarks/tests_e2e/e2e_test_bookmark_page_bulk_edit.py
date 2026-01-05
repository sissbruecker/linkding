from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.models import Bookmark
from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class BookmarkPageBulkEditE2ETestCase(LinkdingE2ETestCase):
    def setup_test_data(self):
        self.setup_numbered_bookmarks(50)
        self.setup_numbered_bookmarks(50, archived=True)
        self.setup_numbered_bookmarks(50, prefix="foo")
        self.setup_numbered_bookmarks(50, archived=True, prefix="foo")

        self.assertEqual(
            50,
            Bookmark.objects.filter(
                is_archived=False, title__startswith="Bookmark"
            ).count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(
                is_archived=True, title__startswith="Archived Bookmark"
            ).count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(is_archived=False, title__startswith="foo").count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(is_archived=True, title__startswith="foo").count(),
        )

    def test_active_bookmarks_bulk_select_across(self):
        self.setup_test_data()

        self.open(reverse("linkding:bookmarks.index"))

        bookmark_list = self.locate_bookmark_list().element_handle()
        self.locate_bulk_edit_toggle().click()
        self.locate_bulk_edit_select_all().click()
        self.locate_bulk_edit_select_across().click()

        self.select_bulk_action("Delete")
        self.locate_bulk_edit_bar().get_by_text("Execute").click()
        self.locate_confirm_dialog().get_by_text("Confirm").click()
        # Wait until bookmark list is updated (old reference becomes invisible)
        bookmark_list.wait_for_element_state("hidden", timeout=1000)

        self.assertEqual(
            0,
            Bookmark.objects.filter(
                is_archived=False, title__startswith="Bookmark"
            ).count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(
                is_archived=True, title__startswith="Archived Bookmark"
            ).count(),
        )
        self.assertEqual(
            0,
            Bookmark.objects.filter(is_archived=False, title__startswith="foo").count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(is_archived=True, title__startswith="foo").count(),
        )

    def test_archived_bookmarks_bulk_select_across(self):
        self.setup_test_data()

        self.open(reverse("linkding:bookmarks.archived"))

        bookmark_list = self.locate_bookmark_list().element_handle()
        self.locate_bulk_edit_toggle().click()
        self.locate_bulk_edit_select_all().click()
        self.locate_bulk_edit_select_across().click()

        self.select_bulk_action("Delete")
        self.locate_bulk_edit_bar().get_by_text("Execute").click()
        self.locate_confirm_dialog().get_by_text("Confirm").click()
        # Wait until bookmark list is updated (old reference becomes invisible)
        bookmark_list.wait_for_element_state("hidden", timeout=1000)

        self.assertEqual(
            50,
            Bookmark.objects.filter(
                is_archived=False, title__startswith="Bookmark"
            ).count(),
        )
        self.assertEqual(
            0,
            Bookmark.objects.filter(
                is_archived=True, title__startswith="Archived Bookmark"
            ).count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(is_archived=False, title__startswith="foo").count(),
        )
        self.assertEqual(
            0,
            Bookmark.objects.filter(is_archived=True, title__startswith="foo").count(),
        )

    def test_active_bookmarks_bulk_select_across_respects_query(self):
        self.setup_test_data()

        self.open(reverse("linkding:bookmarks.index") + "?q=foo")

        bookmark_list = self.locate_bookmark_list().element_handle()
        self.locate_bulk_edit_toggle().click()
        self.locate_bulk_edit_select_all().click()
        self.locate_bulk_edit_select_across().click()

        self.select_bulk_action("Delete")
        self.locate_bulk_edit_bar().get_by_text("Execute").click()
        self.locate_confirm_dialog().get_by_text("Confirm").click()
        # Wait until bookmark list is updated (old reference becomes invisible)
        bookmark_list.wait_for_element_state("hidden", timeout=1000)

        self.assertEqual(
            50,
            Bookmark.objects.filter(
                is_archived=False, title__startswith="Bookmark"
            ).count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(
                is_archived=True, title__startswith="Archived Bookmark"
            ).count(),
        )
        self.assertEqual(
            0,
            Bookmark.objects.filter(is_archived=False, title__startswith="foo").count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(is_archived=True, title__startswith="foo").count(),
        )

    def test_archived_bookmarks_bulk_select_across_respects_query(self):
        self.setup_test_data()

        self.open(reverse("linkding:bookmarks.archived") + "?q=foo")

        bookmark_list = self.locate_bookmark_list().element_handle()
        self.locate_bulk_edit_toggle().click()
        self.locate_bulk_edit_select_all().click()
        self.locate_bulk_edit_select_across().click()

        self.select_bulk_action("Delete")
        self.locate_bulk_edit_bar().get_by_text("Execute").click()
        self.locate_confirm_dialog().get_by_text("Confirm").click()
        # Wait until bookmark list is updated (old reference becomes invisible)
        bookmark_list.wait_for_element_state("hidden", timeout=1000)

        self.assertEqual(
            50,
            Bookmark.objects.filter(
                is_archived=False, title__startswith="Bookmark"
            ).count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(
                is_archived=True, title__startswith="Archived Bookmark"
            ).count(),
        )
        self.assertEqual(
            50,
            Bookmark.objects.filter(is_archived=False, title__startswith="foo").count(),
        )
        self.assertEqual(
            0,
            Bookmark.objects.filter(is_archived=True, title__startswith="foo").count(),
        )

    def test_select_all_toggles_all_checkboxes(self):
        self.setup_numbered_bookmarks(5)

        url = reverse("linkding:bookmarks.index")
        page = self.open(url)

        self.locate_bulk_edit_toggle().click()

        checkboxes = page.locator("label.bulk-edit-checkbox input")
        self.assertEqual(6, checkboxes.count())
        for i in range(checkboxes.count()):
            expect(checkboxes.nth(i)).not_to_be_checked()

        self.locate_bulk_edit_select_all().click()

        for i in range(checkboxes.count()):
            expect(checkboxes.nth(i)).to_be_checked()

        self.locate_bulk_edit_select_all().click()

        for i in range(checkboxes.count()):
            expect(checkboxes.nth(i)).not_to_be_checked()

    def test_select_all_shows_select_across(self):
        self.setup_numbered_bookmarks(5)

        url = reverse("linkding:bookmarks.index")
        self.open(url)

        self.locate_bulk_edit_toggle().click()

        expect(self.locate_bulk_edit_select_across()).not_to_be_visible()

        self.locate_bulk_edit_select_all().click()
        expect(self.locate_bulk_edit_select_across()).to_be_visible()

        self.locate_bulk_edit_select_all().click()
        expect(self.locate_bulk_edit_select_across()).not_to_be_visible()

    def test_select_across_is_unchecked_when_toggling_all(self):
        self.setup_numbered_bookmarks(5)

        url = reverse("linkding:bookmarks.index")
        self.open(url)

        self.locate_bulk_edit_toggle().click()

        # Show select across, check it
        self.locate_bulk_edit_select_all().click()
        self.locate_bulk_edit_select_across().click()
        expect(self.locate_bulk_edit_select_across()).to_be_checked()

        # Hide select across by toggling select all
        self.locate_bulk_edit_select_all().click()
        expect(self.locate_bulk_edit_select_across()).not_to_be_visible()

        # Show select across again, verify it is unchecked
        self.locate_bulk_edit_select_all().click()
        expect(self.locate_bulk_edit_select_across()).not_to_be_checked()

    def test_select_across_is_unchecked_when_toggling_bookmark(self):
        self.setup_numbered_bookmarks(5)

        url = reverse("linkding:bookmarks.index")
        self.open(url)

        self.locate_bulk_edit_toggle().click()

        # Show select across, check it
        self.locate_bulk_edit_select_all().click()
        self.locate_bulk_edit_select_across().click()
        expect(self.locate_bulk_edit_select_across()).to_be_checked()

        # Hide select across by toggling a single bookmark
        self.locate_bookmark("Bookmark 1").locator("label.bulk-edit-checkbox").click()
        expect(self.locate_bulk_edit_select_across()).not_to_be_visible()

        # Show select across again, verify it is unchecked
        self.locate_bookmark("Bookmark 1").locator("label.bulk-edit-checkbox").click()
        expect(self.locate_bulk_edit_select_across()).not_to_be_checked()

    def test_execute_resets_all_checkboxes(self):
        self.setup_numbered_bookmarks(100)

        url = reverse("linkding:bookmarks.index")
        page = self.open(url)

        bookmark_list = self.locate_bookmark_list().element_handle()

        # Select all bookmarks, enable select across
        self.locate_bulk_edit_toggle().click()
        self.locate_bulk_edit_select_all().click()
        self.locate_bulk_edit_select_across().click()

        # Execute bulk action
        self.select_bulk_action("Mark as unread")
        self.locate_bulk_edit_bar().get_by_text("Execute").click()
        self.locate_confirm_dialog().get_by_text("Confirm").click()

        # Wait until bookmark list is updated (old reference becomes invisible)
        bookmark_list.wait_for_element_state("hidden", timeout=1000)

        # Verify bulk edit checkboxes are reset
        checkboxes = page.locator("label.bulk-edit-checkbox input")
        self.assertEqual(31, checkboxes.count())
        for i in range(checkboxes.count()):
            expect(checkboxes.nth(i)).not_to_be_checked()

        # Toggle select all and verify select across is reset
        self.locate_bulk_edit_select_all().click()
        expect(self.locate_bulk_edit_select_across()).not_to_be_checked()

    def test_update_select_across_bookmark_count(self):
        self.setup_numbered_bookmarks(100)

        url = reverse("linkding:bookmarks.index")
        self.open(url)

        bookmark_list = self.locate_bookmark_list().element_handle()
        self.locate_bulk_edit_toggle().click()
        self.locate_bulk_edit_select_all().click()

        expect(
            self.locate_bulk_edit_bar().get_by_text("All 100 bookmarks")
        ).to_be_visible()

        self.select_bulk_action("Delete")
        self.locate_bulk_edit_bar().get_by_text("Execute").click()
        self.locate_confirm_dialog().get_by_text("Confirm").click()
        # Wait until bookmark list is updated (old reference becomes invisible)
        bookmark_list.wait_for_element_state("hidden", timeout=1000)

        expect(self.locate_bulk_edit_select_all()).not_to_be_checked()
        self.locate_bulk_edit_select_all().click()

        expect(
            self.locate_bulk_edit_bar().get_by_text("All 70 bookmarks")
        ).to_be_visible()

    def test_execute_button_is_disabled_when_no_bookmarks_selected(self):
        self.setup_numbered_bookmarks(5)

        url = reverse("linkding:bookmarks.index")
        self.open(url)

        self.locate_bulk_edit_toggle().click()

        execute_button = self.locate_bulk_edit_bar().get_by_text("Execute")

        # Execute button should be disabled by default
        expect(execute_button).to_be_disabled()

        # Check a single bookmark - execute button should be enabled
        self.locate_bookmark("Bookmark 1").locator("label.bulk-edit-checkbox").click()
        expect(execute_button).to_be_enabled()

        # Uncheck the bookmark - execute button should be disabled again
        self.locate_bookmark("Bookmark 1").locator("label.bulk-edit-checkbox").click()
        expect(execute_button).to_be_disabled()

        # Check all bookmarks - execute button should be enabled
        self.locate_bulk_edit_select_all().click()
        expect(execute_button).to_be_enabled()

        # Uncheck all bookmarks - execute button should be disabled again
        self.locate_bulk_edit_select_all().click()
        expect(execute_button).to_be_disabled()
