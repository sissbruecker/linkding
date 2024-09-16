from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase


class TagCloudModalE2ETestCase(LinkdingE2ETestCase):
    def test_show_modal_close_modal(self):
        self.setup_bookmark(tags=[self.setup_tag(name="cooking")])
        self.setup_bookmark(tags=[self.setup_tag(name="hiking")])

        with sync_playwright() as p:
            page = self.open(reverse("bookmarks:index"), p)

            # use smaller viewport to make tags button visible
            page.set_viewport_size({"width": 375, "height": 812})

            # open tag cloud modal
            modal_trigger = page.locator(".content-area-header").get_by_role(
                "button", name="Tags"
            )
            modal_trigger.click()

            # verify modal is visible
            modal = page.locator(".modal")
            expect(modal).to_be_visible()
            expect(modal.locator("h2")).to_have_text("Tags")

            # close with close button
            modal.locator("button.close").click()
            expect(modal).to_be_hidden()

            # open modal again
            modal_trigger.click()

            # close with backdrop
            backdrop = modal.locator(".modal-overlay")
            backdrop.click(position={"x": 0, "y": 0})
            expect(modal).to_be_hidden()

    def test_select_tag(self):
        self.setup_bookmark(tags=[self.setup_tag(name="cooking")])
        self.setup_bookmark(tags=[self.setup_tag(name="hiking")])

        with sync_playwright() as p:
            page = self.open(reverse("bookmarks:index"), p)

            # use smaller viewport to make tags button visible
            page.set_viewport_size({"width": 375, "height": 812})

            # open tag cloud modal
            modal_trigger = page.locator(".content-area-header").get_by_role(
                "button", name="Tags"
            )
            modal_trigger.click()

            # verify tags are displayed
            modal = page.locator(".modal")
            unselected_tags = modal.locator(".unselected-tags")
            expect(unselected_tags.get_by_text("cooking")).to_be_visible()
            expect(unselected_tags.get_by_text("hiking")).to_be_visible()

            # select tag
            unselected_tags.get_by_text("cooking").click()

            # open modal again
            modal_trigger.click()

            # verify tag is selected, other tag is not visible anymore
            selected_tags = modal.locator(".selected-tags")
            expect(selected_tags.get_by_text("cooking")).to_be_visible()

            expect(unselected_tags.get_by_text("cooking")).not_to_be_visible()
            expect(unselected_tags.get_by_text("hiking")).not_to_be_visible()
