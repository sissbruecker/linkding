import os

from django.contrib.staticfiles.testing import LiveServerTestCase
from playwright.sync_api import BrowserContext, Page, expect, sync_playwright

from bookmarks.tests.helpers import BookmarkFactoryMixin

SCREENSHOT_DIR = "test-results/screenshots"

# Allow Django ORM operations within Playwright's async context
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


class LinkdingE2ETestCase(LiveServerTestCase, BookmarkFactoryMixin):
    def setUp(self) -> None:
        self.client.force_login(self.get_or_create_test_user())
        self.cookie = self.client.cookies["sessionid"]
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def tearDown(self) -> None:
        if self.page and self._test_has_failed():
            self._capture_screenshot()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        super().tearDown()

    def _test_has_failed(self) -> bool:
        """Detect if the current test has failed. Works with both Django/unittest and pytest."""
        # Check _outcome for failure info
        if self._outcome is not None:
            result = self._outcome.result
            if result:
                # pytest stores exception info in _excinfo
                if hasattr(result, "_excinfo") and result._excinfo:
                    return True
                # Django/unittest stores failures and errors in the result
                # Check if THIS test is in failures/errors (not just any test)
                if hasattr(result, "failures"):
                    for failed_test, _ in result.failures:
                        if failed_test is self:
                            return True
        return False

    def _ensure_playwright(self):
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)

    def _capture_screenshot(self):
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        filename = f"{self.__class__.__name__}_{self._testMethodName}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        self.page.screenshot(path=filepath, full_page=True)

    def setup_browser(self) -> BrowserContext:
        self._ensure_playwright()
        context = self.browser.new_context()
        context.add_cookies(
            [
                {
                    "name": "sessionid",
                    "value": self.cookie.value,
                    "domain": self.live_server_url.replace("http:", ""),
                    "path": "/",
                }
            ]
        )
        return context

    def open(self, url: str) -> Page:
        self.context = self.setup_browser()
        self.page = self.context.new_page()
        self.page.on("pageerror", self.on_page_error)
        self.page.goto(self.live_server_url + url)
        self.page.on("load", self.on_load)
        self.num_loads = 0
        return self.page

    def on_page_error(self, error):
        print(f"[JS ERROR] {error}")
        if hasattr(error, "stack"):
            print(f"[JS STACK] {error.stack}")

    def on_load(self):
        self.num_loads += 1

    def assertReloads(self, count: int):
        self.assertEqual(self.num_loads, count)

    def resetReloads(self):
        self.num_loads = 0

    def locate_bookmark_list(self):
        return self.page.locator("ul.bookmark-list")

    def locate_bookmark(self, title: str):
        bookmark_tags = self.page.locator("ul.bookmark-list > li")
        return bookmark_tags.filter(has_text=title)

    def count_bookmarks(self):
        bookmark_tags = self.page.locator("ul.bookmark-list > li")
        return bookmark_tags.count()

    def locate_details_modal(self):
        return self.page.locator("ld-details-modal")

    def open_details_modal(self, bookmark):
        details_button = self.locate_bookmark(bookmark.title).get_by_text("View")
        details_button.click()

        details_modal = self.locate_details_modal()
        expect(details_modal).to_be_visible()

        return details_modal

    def locate_bulk_edit_bar(self):
        return self.page.locator(".bulk-edit-bar")

    def locate_bulk_edit_select_all(self):
        return self.locate_bulk_edit_bar().locator("label.bulk-edit-checkbox.all")

    def locate_bulk_edit_select_across(self):
        return self.locate_bulk_edit_bar().locator("label.select-across")

    def locate_bulk_edit_toggle(self):
        return self.page.get_by_title("Bulk edit")

    def select_bulk_action(self, value: str):
        return (
            self.locate_bulk_edit_bar()
            .locator('select[name="bulk_action"]')
            .select_option(value)
        )

    def navigate_menu(self, main_menu_item: str, sub_menu_item: str | None = None):
        if sub_menu_item:
            self.page.locator("nav").get_by_role("button", name=main_menu_item).click()
            self.page.locator("nav ul.menu").get_by_text(
                sub_menu_item, exact=True
            ).click()
        else:
            self.page.locator("nav").get_by_text(main_menu_item, exact=True).click()

    def locate_confirm_dialog(self):
        return self.page.locator("ld-confirm-dropdown")
