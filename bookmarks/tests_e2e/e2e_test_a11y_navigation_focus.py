from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class A11yNavigationFocusTest(LinkdingE2ETestCase):
    def test_initial_page_load_focus(self):
        with sync_playwright() as p:
            # First page load should keep focus on the body
            page = self.open(reverse("linkding:bookmarks.index"), p)
            focused_tag = page.evaluate("document.activeElement?.tagName")
            self.assertEqual("BODY", focused_tag)

            page.goto(self.live_server_url + reverse("linkding:bookmarks.archived"))
            focused_tag = page.evaluate("document.activeElement?.tagName")
            self.assertEqual("BODY", focused_tag)

            page.goto(self.live_server_url + reverse("linkding:settings.general"))
            focused_tag = page.evaluate("document.activeElement?.tagName")
            self.assertEqual("BODY", focused_tag)

            # Bookmark form views should focus the URL input
            page.goto(self.live_server_url + reverse("linkding:bookmarks.new"))
            focused_tag = page.evaluate(
                "document.activeElement?.tagName + '|' + document.activeElement?.name"
            )
            self.assertEqual("INPUT|url", focused_tag)

    def test_page_navigation_focus(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            page = self.open(reverse("linkding:bookmarks.index"), p)

            # Subsequent navigation should move focus to main content
            self.reset_focus()
            self.navigate_menu("Bookmarks", "Active")
            focused = page.locator("main:focus")
            expect(focused).to_be_visible()

            self.reset_focus()
            self.navigate_menu("Bookmarks", "Archived")
            focused = page.locator("main:focus")
            expect(focused).to_be_visible()

            self.reset_focus()
            self.navigate_menu("Settings", "General")
            focused = page.locator("main:focus")
            expect(focused).to_be_visible()

            # Bookmark form views should focus the URL input
            self.reset_focus()
            self.navigate_menu("Add bookmark")
            focused = page.locator("input[name='url']:focus")
            expect(focused).to_be_visible()

            # Opening details modal should move focus to close button
            self.navigate_menu("Bookmarks", "Active")
            self.open_details_modal(bookmark)
            focused = page.locator(".modal button.close:focus")
            expect(focused).to_be_visible()

            # Closing modal should move focus back to the bookmark item
            page.keyboard.press("Escape")
            focused = self.locate_bookmark(bookmark.title).locator(
                "a.view-action:focus"
            )
            expect(focused).to_be_visible()

    def reset_focus(self):
        self.page.evaluate("document.activeElement.blur()")
