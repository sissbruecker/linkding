from unittest import skip

from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class BookmarkItemE2ETestCase(LinkdingE2ETestCase):
    @skip("Fails in CI, needs investigation")
    def test_toggle_notes_should_show_hide_notes(self):
        bookmark = self.setup_bookmark(notes="Test notes")

        page = self.open(reverse("linkding:bookmarks.index"))

        notes = self.locate_bookmark(bookmark.title).locator(".notes")
        expect(notes).to_be_hidden()

        toggle_notes = page.locator("li button.toggle-notes")
        toggle_notes.click()
        expect(notes).to_be_visible()

        toggle_notes.click()
        expect(notes).to_be_hidden()
