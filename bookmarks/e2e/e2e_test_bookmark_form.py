from unittest.mock import patch

from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase
from bookmarks.services import website_loader


class BookmarkFormE2ETestCase(LinkdingE2ETestCase):
    def test_create_enter_url_prefills_title_and_description(self):
        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            mock_load_website_metadata.return_value = website_loader.WebsiteMetadata(
                url="https://example.com",
                title="Example Domain",
                description="This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.",
                preview_image=None,
            )

            with sync_playwright() as p:
                page = self.open(reverse("bookmarks:new"), p)

                page.get_by_label("URL").fill("https://example.com")

                title = page.get_by_label("Title")
                description = page.get_by_label("Description")
                expect(title).to_have_value("Example Domain")
                expect(description).to_have_value(
                    "This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission."
                )

    def test_create_should_check_for_existing_bookmark(self):
        existing_bookmark = self.setup_bookmark(
            title="Existing title",
            description="Existing description",
            notes="Existing notes",
            tags=[self.setup_tag(name="tag1"), self.setup_tag(name="tag2")],
            unread=True,
        )
        tag_names = " ".join(existing_bookmark.tag_names)

        with sync_playwright() as p:
            page = self.open(reverse("bookmarks:new"), p)

            # Enter bookmarked URL
            page.get_by_label("URL").fill(existing_bookmark.url)
            # Already bookmarked hint should be visible
            page.get_by_text("This URL is already bookmarked.").wait_for(timeout=2000)
            # Form should be pre-filled with data from existing bookmark
            self.assertEqual(
                existing_bookmark.title, page.get_by_label("Title").input_value()
            )
            self.assertEqual(
                existing_bookmark.description,
                page.get_by_label("Description").input_value(),
            )
            self.assertEqual(
                existing_bookmark.notes, page.get_by_label("Notes").input_value()
            )
            self.assertEqual(tag_names, page.get_by_label("Tags").input_value())
            self.assertTrue(tag_names, page.get_by_label("Mark as unread").is_checked())

            # Enter non-bookmarked URL
            page.get_by_label("URL").fill("https://example.com/unknown")
            # Already bookmarked hint should be hidden
            page.get_by_text("This URL is already bookmarked.").wait_for(
                state="hidden", timeout=2000
            )

    def test_edit_should_not_check_for_existing_bookmark(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            page = self.open(reverse("bookmarks:edit", args=[bookmark.id]), p)

            page.wait_for_timeout(timeout=1000)
            page.get_by_text("This URL is already bookmarked.").wait_for(state="hidden")

    def test_edit_should_not_prefill_title_and_description(self):
        bookmark = self.setup_bookmark()
        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            mock_load_website_metadata.return_value = website_loader.WebsiteMetadata(
                url="https://example.com",
                title="Example Domain",
                description="This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.",
                preview_image=None,
            )

            with sync_playwright() as p:
                page = self.open(reverse("bookmarks:edit", args=[bookmark.id]), p)
                page.wait_for_timeout(timeout=1000)

                title = page.get_by_label("Title")
                description = page.get_by_label("Description")
                expect(title).to_have_value(bookmark.title)
                expect(description).to_have_value(bookmark.description)

    def test_edit_enter_url_should_not_prefill_title_and_description(self):
        bookmark = self.setup_bookmark()
        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            mock_load_website_metadata.return_value = website_loader.WebsiteMetadata(
                url="https://example.com",
                title="Example Domain",
                description="This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.",
                preview_image=None,
            )

            with sync_playwright() as p:
                page = self.open(reverse("bookmarks:edit", args=[bookmark.id]), p)

                page.get_by_label("URL").fill("https://example.com")
                page.wait_for_timeout(timeout=1000)

                title = page.get_by_label("Title")
                description = page.get_by_label("Description")
                expect(title).to_have_value(bookmark.title)
                expect(description).to_have_value(bookmark.description)

    def test_enter_url_of_existing_bookmark_should_show_notes(self):
        bookmark = self.setup_bookmark(
            notes="Existing notes", description="Existing description"
        )

        with sync_playwright() as p:
            page = self.open(reverse("bookmarks:new"), p)

            details = page.locator("details.notes")
            expect(details).not_to_have_attribute("open", value="")

            page.get_by_label("URL").fill(bookmark.url)
            expect(details).to_have_attribute("open", value="")

    def test_create_should_preview_auto_tags(self):
        profile = self.get_or_create_test_user().profile
        profile.auto_tagging_rules = "github.com dev github"
        profile.save()

        with sync_playwright() as p:
            # Open page with URL that should have auto tags
            url = (
                reverse("bookmarks:new")
                + "?url=https%3A%2F%2Fgithub.com%2Fsissbruecker%2Flinkding"
            )
            page = self.open(url, p)

            auto_tags_hint = page.locator(".form-input-hint.auto-tags")
            expect(auto_tags_hint).to_be_visible()
            expect(auto_tags_hint).to_have_text("Auto tags: dev github")

            # Change to URL without auto tags
            page.get_by_label("URL").fill("https://example.com")

            expect(auto_tags_hint).to_be_hidden()
