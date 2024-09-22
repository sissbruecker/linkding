from unittest.mock import patch

from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase
from bookmarks.services import website_loader

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
        super().tearDown()
        self.website_loader_patch.stop()

    def test_should_not_check_for_existing_bookmark(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            page = self.open(reverse("bookmarks:edit", args=[bookmark.id]), p)

            page.wait_for_timeout(timeout=1000)
            page.get_by_text("This URL is already bookmarked.").wait_for(state="hidden")

    def test_should_not_prefill_title_and_description(self):
        bookmark = self.setup_bookmark(
            title="Initial title", description="Initial description"
        )

        with sync_playwright() as p:
            page = self.open(reverse("bookmarks:edit", args=[bookmark.id]), p)
            page.wait_for_timeout(timeout=1000)

            title = page.get_by_label("Title")
            description = page.get_by_label("Description")
            expect(title).to_have_value(bookmark.title)
            expect(description).to_have_value(bookmark.description)

    def test_enter_url_should_not_prefill_title_and_description(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            page = self.open(reverse("bookmarks:edit", args=[bookmark.id]), p)

            page.get_by_label("URL").fill("https://example.com")
            page.wait_for_timeout(timeout=1000)

            title = page.get_by_label("Title")
            description = page.get_by_label("Description")
            expect(title).to_have_value(bookmark.title)
            expect(description).to_have_value(bookmark.description)
