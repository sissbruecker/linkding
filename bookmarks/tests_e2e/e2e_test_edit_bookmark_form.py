from unittest.mock import patch

from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.services import website_loader
from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase

mock_website_metadata = website_loader.WebsiteMetadata(
    url="https://example.com",
    title="Example Domain",
    description="This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.",
    preview_image=None,
)


class BookmarkFormE2ETestCase(LinkdingE2ETestCase):
    def setUp(self) -> None:
        super().setUp()
        self.website_loader_patch = patch.object(
            website_loader, "load_website_metadata", return_value=mock_website_metadata
        )
        self.website_loader_patch.start()

    def tearDown(self) -> None:
        self.website_loader_patch.stop()
        super().tearDown()

    def test_should_not_check_for_existing_bookmark(self):
        bookmark = self.setup_bookmark()

        page = self.open(reverse("linkding:bookmarks.edit", args=[bookmark.id]))

        page.wait_for_timeout(timeout=1000)
        page.get_by_text("This URL is already bookmarked.").wait_for(state="hidden")

    def test_should_not_prefill_title_and_description(self):
        bookmark = self.setup_bookmark(
            title="Initial title", description="Initial description"
        )

        page = self.open(reverse("linkding:bookmarks.edit", args=[bookmark.id]))
        page.wait_for_timeout(timeout=1000)

        title = page.get_by_label("Title")
        description = page.get_by_label("Description")
        expect(title).to_have_value(bookmark.title)
        expect(description).to_have_value(bookmark.description)

    def test_enter_url_should_not_prefill_title_and_description(self):
        bookmark = self.setup_bookmark()

        page = self.open(reverse("linkding:bookmarks.edit", args=[bookmark.id]))

        page.get_by_label("URL").fill("https://example.com")
        page.wait_for_timeout(timeout=1000)

        title = page.get_by_label("Title")
        description = page.get_by_label("Description")
        expect(title).to_have_value(bookmark.title)
        expect(description).to_have_value(bookmark.description)

    def test_refresh_button_should_be_visible_when_editing(self):
        bookmark = self.setup_bookmark()

        page = self.open(reverse("linkding:bookmarks.edit", args=[bookmark.id]))

        refresh_button = page.get_by_text("Refresh from website")
        expect(refresh_button).to_be_visible()
