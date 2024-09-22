from django.test import override_settings
from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase
from bookmarks.models import Bookmark


class BookmarkDetailsModalE2ETestCase(LinkdingE2ETestCase):
    def test_show_details(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            self.open(reverse("bookmarks:index"), p)

            details_modal = self.open_details_modal(bookmark)
            title = details_modal.locator("h2")
            expect(title).to_have_text(bookmark.title)

    def test_close_details(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            self.open(reverse("bookmarks:index"), p)

            # close with close button
            details_modal = self.open_details_modal(bookmark)
            details_modal.locator("button.close").click()
            expect(details_modal).to_be_hidden()

            # close with backdrop
            details_modal = self.open_details_modal(bookmark)
            overlay = details_modal.locator(".modal-overlay")
            overlay.click(position={"x": 0, "y": 0})
            expect(details_modal).to_be_hidden()

            # close with escape
            details_modal = self.open_details_modal(bookmark)
            self.page.keyboard.press("Escape")
            expect(details_modal).to_be_hidden()

    def test_toggle_archived(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            # archive
            url = reverse("bookmarks:index")
            self.open(url, p)

            details_modal = self.open_details_modal(bookmark)
            details_modal.get_by_text("Archived", exact=False).click()
            expect(self.locate_bookmark(bookmark.title)).not_to_be_visible()
            self.assertReloads(0)

            # unarchive
            url = reverse("bookmarks:archived")
            self.page.goto(self.live_server_url + url)
            self.resetReloads()

            details_modal = self.open_details_modal(bookmark)
            details_modal.get_by_text("Archived", exact=False).click()
            expect(self.locate_bookmark(bookmark.title)).not_to_be_visible()
            self.assertReloads(0)

    def test_toggle_unread(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            # mark as unread
            url = reverse("bookmarks:index")
            self.open(url, p)

            details_modal = self.open_details_modal(bookmark)

            details_modal.get_by_text("Unread").click()
            bookmark_item = self.locate_bookmark(bookmark.title)
            expect(bookmark_item.get_by_text("Unread")).to_be_visible()
            self.assertReloads(0)

            # mark as read
            details_modal.get_by_text("Unread").click()
            bookmark_item = self.locate_bookmark(bookmark.title)
            expect(bookmark_item.get_by_text("Unread")).not_to_be_visible()
            self.assertReloads(0)

    def test_toggle_shared(self):
        profile = self.get_or_create_test_user().profile
        profile.enable_sharing = True
        profile.save()

        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            # share bookmark
            url = reverse("bookmarks:index")
            self.open(url, p)

            details_modal = self.open_details_modal(bookmark)

            details_modal.get_by_text("Shared").click()
            bookmark_item = self.locate_bookmark(bookmark.title)
            expect(bookmark_item.get_by_text("Shared")).to_be_visible()
            self.assertReloads(0)

            # unshare bookmark
            details_modal.get_by_text("Shared").click()
            bookmark_item = self.locate_bookmark(bookmark.title)
            expect(bookmark_item.get_by_text("Shared")).not_to_be_visible()
            self.assertReloads(0)

    def test_edit_return_url(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            url = reverse("bookmarks:index") + f"?q={bookmark.title}"
            self.open(url, p)

            details_modal = self.open_details_modal(bookmark)

            # Navigate to edit page
            with self.page.expect_navigation():
                details_modal.get_by_text("Edit").click()

            # Cancel edit, verify return to details url
            details_url = url + f"&details={bookmark.id}"
            with self.page.expect_navigation(url=self.live_server_url + details_url):
                self.page.get_by_text("Nevermind").click()

    def test_delete(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            url = reverse("bookmarks:index") + f"?q={bookmark.title}"
            self.open(url, p)

            details_modal = self.open_details_modal(bookmark)

            # Wait for confirm button to be initialized
            self.page.wait_for_timeout(1000)

            # Delete bookmark, verify return url
            with self.page.expect_navigation(url=self.live_server_url + url):
                details_modal.get_by_text("Delete...").click()
                details_modal.get_by_text("Confirm").click()

            # verify bookmark is deleted
            self.locate_bookmark(bookmark.title)
            expect(self.locate_bookmark(bookmark.title)).not_to_be_visible()

        self.assertEqual(Bookmark.objects.count(), 0)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_snapshot_remove_snapshot(self):
        bookmark = self.setup_bookmark()

        with sync_playwright() as p:
            url = reverse("bookmarks:index") + f"?q={bookmark.title}"
            self.open(url, p)

            details_modal = self.open_details_modal(bookmark)
            asset_list = details_modal.locator(".assets")

            # No snapshots initially
            snapshot = asset_list.get_by_text("HTML snapshot from", exact=False)
            expect(snapshot).not_to_be_visible()

            # Create snapshot
            details_modal.get_by_text("Create HTML snapshot", exact=False).click()
            self.assertReloads(0)

            # Has new snapshots
            expect(snapshot).to_be_visible()

            # Remove snapshot
            asset_list.get_by_text("Remove", exact=False).click()
            asset_list.get_by_text("Confirm", exact=False).click()

            # Snapshot is removed
            expect(snapshot).not_to_be_visible()
            self.assertReloads(0)
