from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class DropdownE2ETestCase(LinkdingE2ETestCase):
    def locate_dropdown(self):
        # Use bookmarks dropdown as an example instance to test
        return self.page.locator("ld-dropdown").filter(
            has=self.page.get_by_role("button", name="Bookmarks")
        )

    def locate_dropdown_toggle(self):
        return self.locate_dropdown().locator(".dropdown-toggle")

    def locate_dropdown_menu(self):
        return self.locate_dropdown().locator(".menu")

    def test_click_toggle_opens_and_closes_dropdown(self):
        self.open(reverse("linkding:bookmarks.index"))

        toggle = self.locate_dropdown_toggle()
        menu = self.locate_dropdown_menu()

        # Open dropdown
        toggle.click()
        expect(menu).to_be_visible()

        # Click toggle again to close
        toggle.click()
        expect(menu).not_to_be_visible()

    def test_outside_click_closes_dropdown(self):
        self.open(reverse("linkding:bookmarks.index"))

        toggle = self.locate_dropdown_toggle()
        menu = self.locate_dropdown_menu()

        # Open dropdown
        toggle.click()
        expect(menu).to_be_visible()

        # Click outside the dropdown (on the page body)
        self.page.locator("main").click()
        expect(menu).not_to_be_visible()

    def test_escape_closes_dropdown_and_restores_focus(self):
        self.open(reverse("linkding:bookmarks.index"))

        toggle = self.locate_dropdown_toggle()
        menu = self.locate_dropdown_menu()

        # Open dropdown
        toggle.click()
        expect(menu).to_be_visible()

        # Press Escape
        self.page.keyboard.press("Escape")

        # Menu should be closed
        expect(menu).not_to_be_visible()

        # Focus should be back on toggle
        expect(toggle).to_be_focused()

    def test_focus_out_closes_dropdown(self):
        self.open(reverse("linkding:bookmarks.index"))

        toggle = self.locate_dropdown_toggle()
        menu = self.locate_dropdown_menu()

        # Open dropdown
        toggle.click()
        expect(menu).to_be_visible()

        # Shift+Tab to move focus out of the dropdown
        self.page.keyboard.press("Shift+Tab")

        # Menu should be closed after focus leaves
        expect(menu).not_to_be_visible()

    def test_aria_expanded_attribute(self):
        self.open(reverse("linkding:bookmarks.index"))

        toggle = self.locate_dropdown_toggle()
        menu = self.locate_dropdown_menu()

        # Initially aria-expanded should be false
        expect(toggle).to_have_attribute("aria-expanded", "false")

        # Open dropdown
        toggle.click()
        expect(menu).to_be_visible()

        # aria-expanded should be true
        expect(toggle).to_have_attribute("aria-expanded", "true")

        # Close dropdown
        toggle.click()
        expect(menu).not_to_be_visible()

        # aria-expanded should be false again
        expect(toggle).to_have_attribute("aria-expanded", "false")

    def test_can_click_menu_item(self):
        self.open(reverse("linkding:bookmarks.index"))

        toggle = self.locate_dropdown_toggle()
        menu = self.locate_dropdown_menu()

        # Open dropdown
        toggle.click()
        expect(menu).to_be_visible()

        # Click on "Archived" menu item
        menu.get_by_text("Archived", exact=True).click()

        # Should navigate to archived page
        expect(self.page).to_have_url(
            self.live_server_url + reverse("linkding:bookmarks.archived")
        )
