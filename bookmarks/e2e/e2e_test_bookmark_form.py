from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase


class BookmarkFormE2ETestCase(LinkdingE2ETestCase):
    def test_create_should_check_for_existing_bookmark(self):
        existing_bookmark = self.setup_bookmark(
            title="Existing title",
            description="Existing description",
            notes="Existing notes",
            tags=[self.setup_tag(name="tag1"), self.setup_tag(name="tag2")],
            website_title="Existing website title",
            website_description="Existing website description",
            unread=True,
        )
        tag_names = " ".join(existing_bookmark.tag_names)

        with sync_playwright() as p:
            browser = self.setup_browser(p)
            page = browser.new_page()
            page.goto(self.live_server_url + reverse("bookmarks:new"))

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
            self.assertEqual(
                existing_bookmark.website_title,
                page.get_by_label("Title").get_attribute("placeholder"),
            )
            self.assertEqual(
                existing_bookmark.website_description,
                page.get_by_label("Description").get_attribute("placeholder"),
            )
            self.assertEqual(tag_names, page.get_by_label("Tags").input_value())
            self.assertTrue(tag_names, page.get_by_label("Mark as unread").is_checked())

            # Enter non-bookmarked URL
            page.get_by_label("URL").fill("https://example.com/unknown")
            # Already bookmarked hint should be hidden
            page.get_by_text("This URL is already bookmarked.").wait_for(
                state="hidden", timeout=2000
            )

            browser.close()

    def test_edit_should_not_check_for_existing_bookmark(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            browser = self.setup_browser(p)
            page = browser.new_page()
            page.goto(
                self.live_server_url + reverse("bookmarks:edit", args=[bookmark.id])
            )

            page.wait_for_timeout(timeout=1000)
            page.get_by_text("This URL is already bookmarked.").wait_for(state="hidden")

    def test_enter_url_of_existing_bookmark_should_show_notes(self):
        bookmark = self.setup_bookmark(
            notes="Existing notes", description="Existing description"
        )

        with sync_playwright() as p:
            browser = self.setup_browser(p)
            page = browser.new_page()
            page.goto(self.live_server_url + reverse("bookmarks:new"))

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
            browser = self.setup_browser(p)
            page = browser.new_page()
            url = self.live_server_url + reverse("bookmarks:new")
            url += f"?url=https%3A%2F%2Fgithub.com%2Fsissbruecker%2Flinkding"
            page.goto(url)

            auto_tags_hint = page.locator(".form-input-hint.auto-tags")
            expect(auto_tags_hint).to_be_visible()
            expect(auto_tags_hint).to_have_text("Auto tags: dev github")

            # Change to URL without auto tags
            page.get_by_label("URL").fill("https://example.com")

            expect(auto_tags_hint).to_be_hidden()
