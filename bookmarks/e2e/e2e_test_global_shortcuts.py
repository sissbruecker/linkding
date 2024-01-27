from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase


class GlobalShortcutsE2ETestCase(LinkdingE2ETestCase):
    def test_focus_search(self):
        with sync_playwright() as p:
            browser = self.setup_browser(p)
            page = browser.new_page()
            page.goto(self.live_server_url + reverse("bookmarks:index"))

            page.press("body", "s")

            expect(page.get_by_placeholder("Search for words or #tags")).to_be_focused()

            browser.close()

    def test_add_bookmark(self):
        with sync_playwright() as p:
            browser = self.setup_browser(p)
            page = browser.new_page()
            page.goto(self.live_server_url + reverse("bookmarks:index"))

            page.press("body", "n")

            expect(page).to_have_url(self.live_server_url + reverse("bookmarks:new"))

            browser.close()
