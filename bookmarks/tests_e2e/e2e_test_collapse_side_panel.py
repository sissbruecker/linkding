from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class CollapseSidePanelE2ETestCase(LinkdingE2ETestCase):
    def setUp(self) -> None:
        super().setUp()

    def assertSidePanelIsVisible(self):
        expect(self.page.locator(".bookmarks-page .side-panel")).to_be_visible()
        expect(
            self.page.locator(".bookmarks-page ld-filter-drawer-trigger")
        ).not_to_be_visible()

    def assertSidePanelIsHidden(self):
        expect(self.page.locator(".bookmarks-page .side-panel")).not_to_be_visible()
        expect(
            self.page.locator(".bookmarks-page ld-filter-drawer-trigger")
        ).to_be_visible()

    def test_side_panel_should_be_visible_by_default(self):
        self.open(reverse("linkding:bookmarks.index"))
        self.assertSidePanelIsVisible()

        self.page.goto(self.live_server_url + reverse("linkding:bookmarks.archived"))
        self.assertSidePanelIsVisible()

        self.page.goto(self.live_server_url + reverse("linkding:bookmarks.shared"))
        self.assertSidePanelIsVisible()

    def test_side_panel_should_be_hidden_when_collapsed(self):
        user = self.get_or_create_test_user()
        user.profile.collapse_side_panel = True
        user.profile.save()

        self.open(reverse("linkding:bookmarks.index"))
        self.assertSidePanelIsHidden()

        self.page.goto(self.live_server_url + reverse("linkding:bookmarks.archived"))
        self.assertSidePanelIsHidden()

        self.page.goto(self.live_server_url + reverse("linkding:bookmarks.shared"))
        self.assertSidePanelIsHidden()
