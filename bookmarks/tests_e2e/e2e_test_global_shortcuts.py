from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class GlobalShortcutsE2ETestCase(LinkdingE2ETestCase):
    def test_focus_search(self):
        self.open(reverse("linkding:bookmarks.index"))

        self.page.press("body", "s")

        expect(
            self.page.get_by_placeholder("Search for words or #tags")
        ).to_be_focused()

    def test_add_bookmark(self):
        self.open(reverse("linkding:bookmarks.index"))

        self.page.press("body", "n")

        expect(self.page).to_have_url(
            self.live_server_url + reverse("linkding:bookmarks.new")
        )
