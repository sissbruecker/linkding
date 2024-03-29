from django.urls import reverse
from playwright.sync_api import sync_playwright

from bookmarks.e2e.helpers import LinkdingE2ETestCase


class BookmarkDetailsViewE2ETestCase(LinkdingE2ETestCase):
    def test_edit_return_url(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            self.open(reverse("bookmarks:details", args=[bookmark.id]), p)

            # Navigate to edit page
            with self.page.expect_navigation():
                self.page.get_by_text("Edit").click()

            # Cancel edit, verify return url
            with self.page.expect_navigation(
                url=self.live_server_url
                + reverse("bookmarks:details", args=[bookmark.id])
            ):
                self.page.get_by_text("Nevermind").click()

    def test_delete_return_url(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            self.open(reverse("bookmarks:details", args=[bookmark.id]), p)

            # Trigger delete, verify return url
            # Should probably return to last bookmark list page, but for now just returns to index
            with self.page.expect_navigation(
                url=self.live_server_url + reverse("bookmarks:index")
            ):
                self.page.get_by_text("Delete...").click()
                self.page.get_by_text("Confirm").click()
