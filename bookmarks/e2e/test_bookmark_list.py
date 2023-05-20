from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase


class BookmarkListE2ETestCase(LinkdingE2ETestCase):
    def test_toggle_notes_should_show_hide_notes(self):
        self.setup_bookmark(notes='Test notes')

        with sync_playwright() as p:
            browser = self.setup_browser(p)
            page = browser.new_page()
            page.goto(self.live_server_url + reverse('bookmarks:index'))

            notes = page.locator('li .notes')
            expect(notes).to_be_hidden()

            toggle_notes = page.locator('li button.toggle-notes')
            toggle_notes.click()
            expect(notes).to_be_visible()

            toggle_notes.click()
            expect(notes).to_be_hidden()
