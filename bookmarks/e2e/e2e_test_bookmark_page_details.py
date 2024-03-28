from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase
from bookmarks.models import Bookmark


class BookmarkPageDetailsE2ETestCase(LinkdingE2ETestCase):
    def test_show_details(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            self.open(reverse("bookmarks:index"), p)

            details_button = self.locate_bookmark(bookmark.title).get_by_text("View")
            details_button.click()

            details_modal = self.locate_details_modal()
            expect(details_modal).to_be_visible()

            title = details_modal.locator("h2")
            expect(title).to_have_text(bookmark.title)

    def test_close_details(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            self.open(reverse("bookmarks:index"), p)

            # close with close button
            details_button = self.locate_bookmark(bookmark.title).get_by_text("View")
            details_button.click()

            details_modal = self.locate_details_modal()
            expect(details_modal).to_be_visible()

            details_modal.locator("button.close").click()
            expect(details_modal).to_be_hidden()

            # close with backdrop
            details_button.click()

            details_modal = self.locate_details_modal()
            expect(details_modal).to_be_visible()

            overlay = details_modal.locator(".modal-overlay")
            overlay.click(position={"x": 0, "y": 0})
            expect(details_modal).to_be_hidden()

    def test_edit_return_url(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            url = reverse("bookmarks:index") + f"?q={bookmark.title}"
            self.open(url, p)

            details_button = self.locate_bookmark(bookmark.title).get_by_text("View")
            details_button.click()

            details_modal = self.locate_details_modal()
            expect(details_modal).to_be_visible()

            # Navigate to edit page
            with self.page.expect_navigation():
                details_modal.get_by_text("Edit").click()

            # Cancel edit, verify return url
            with self.page.expect_navigation(url=self.live_server_url + url):
                self.page.get_by_text("Nevermind").click()

    def test_delete(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            url = reverse("bookmarks:index") + f"?q={bookmark.title}"
            self.open(url, p)

            details_button = self.locate_bookmark(bookmark.title).get_by_text("View")
            details_button.click()

            details_modal = self.locate_details_modal()
            expect(details_modal).to_be_visible()

            # Delete bookmark, verify return url
            with self.page.expect_navigation(url=self.live_server_url + url):
                details_modal.get_by_text("Delete...").click()
                details_modal.get_by_text("Confirm").click()

            # verify bookmark is deleted
            self.locate_bookmark(bookmark.title)
            self.assertEqual(self.locate_bookmark(bookmark.title).count(), 0)

        self.assertEqual(Bookmark.objects.count(), 0)
