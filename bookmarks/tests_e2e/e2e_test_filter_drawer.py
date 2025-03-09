from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class FilterDrawerE2ETestCase(LinkdingE2ETestCase):
    def test_show_modal_close_modal(self):
        self.setup_bookmark(tags=[self.setup_tag(name="cooking")])
        self.setup_bookmark(tags=[self.setup_tag(name="hiking")])

        with sync_playwright() as p:
            page = self.open(reverse("linkding:bookmarks.index"), p)

            # use smaller viewport to make filter button visible
            page.set_viewport_size({"width": 375, "height": 812})

            # open drawer
            drawer_trigger = page.locator(".content-area-header").get_by_role(
                "button", name="Filters"
            )
            drawer_trigger.click()

            # verify drawer is visible
            drawer = page.locator(".modal.drawer.filter-drawer")
            expect(drawer).to_be_visible()
            expect(drawer.locator("h2")).to_have_text("Filters")

            # close with close button
            drawer.locator("button.close").click()
            expect(drawer).to_be_hidden()

            # open drawer again
            drawer_trigger.click()

            # close with backdrop
            backdrop = drawer.locator(".modal-overlay")
            backdrop.click(position={"x": 0, "y": 0})
            expect(drawer).to_be_hidden()

    def test_select_tag(self):
        self.setup_bookmark(tags=[self.setup_tag(name="cooking")])
        self.setup_bookmark(tags=[self.setup_tag(name="hiking")])

        with sync_playwright() as p:
            page = self.open(reverse("linkding:bookmarks.index"), p)

            # use smaller viewport to make filter button visible
            page.set_viewport_size({"width": 375, "height": 812})

            # open tag cloud modal
            drawer_trigger = page.locator(".content-area-header").get_by_role(
                "button", name="Filters"
            )
            drawer_trigger.click()

            # verify tags are displayed
            drawer = page.locator(".modal.drawer.filter-drawer")
            unselected_tags = drawer.locator(".unselected-tags")
            expect(unselected_tags.get_by_text("cooking")).to_be_visible()
            expect(unselected_tags.get_by_text("hiking")).to_be_visible()

            # select tag
            unselected_tags.get_by_text("cooking").click()

            # open drawer again
            drawer_trigger.click()

            # verify tag is selected, other tag is not visible anymore
            selected_tags = drawer.locator(".selected-tags")
            expect(selected_tags.get_by_text("cooking")).to_be_visible()

            expect(unselected_tags.get_by_text("cooking")).not_to_be_visible()
            expect(unselected_tags.get_by_text("hiking")).not_to_be_visible()
