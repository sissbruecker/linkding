from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class TagsNavigationE2ETestCase(LinkdingE2ETestCase):
    def test_desktop_navigation_opens_tag_management(self):
        page = self.open(reverse("linkding:bookmarks.index"))

        page.locator("nav").get_by_role("link", name="Tags", exact=True).click()

        expect(page).to_have_url(self.live_server_url + reverse("linkding:tags.index"))
        expect(page.get_by_role("heading", name="Tags", exact=True)).to_be_visible()
        expect(page.locator("main")).to_be_focused()

    def test_mobile_navigation_opens_tag_management(self):
        page = self.open(reverse("linkding:bookmarks.index"))
        page.set_viewport_size({"width": 390, "height": 844})

        page.get_by_role("button", name="Navigation menu").click()
        page.locator("nav .show-md").get_by_role(
            "link", name="Tags", exact=True
        ).click()

        expect(page).to_have_url(self.live_server_url + reverse("linkding:tags.index"))
        expect(page.get_by_role("heading", name="Tags", exact=True)).to_be_visible()
        expect(page.locator("main")).to_be_focused()
