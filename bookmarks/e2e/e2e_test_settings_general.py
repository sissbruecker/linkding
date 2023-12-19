from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.e2e.helpers import LinkdingE2ETestCase


class SettingsGeneralE2ETestCase(LinkdingE2ETestCase):
    def test_should_only_enable_public_sharing_if_sharing_is_enabled(self):
        with sync_playwright() as p:
            browser = self.setup_browser(p)
            page = browser.new_page()
            page.goto(self.live_server_url + reverse('bookmarks:settings.general'))

            enable_sharing = page.get_by_label('Enable bookmark sharing')
            enable_sharing_label = page.get_by_text('Enable bookmark sharing')
            enable_public_sharing = page.get_by_label('Enable public bookmark sharing')
            enable_public_sharing_label = page.get_by_text('Enable public bookmark sharing')

            # Public sharing is disabled by default
            expect(enable_sharing).not_to_be_checked()
            expect(enable_public_sharing).not_to_be_checked()
            expect(enable_public_sharing).to_be_disabled()

            # Enable sharing
            enable_sharing_label.click()
            expect(enable_sharing).to_be_checked()
            expect(enable_public_sharing).not_to_be_checked()
            expect(enable_public_sharing).to_be_enabled()

            # Enable public sharing
            enable_public_sharing_label.click()
            expect(enable_public_sharing).to_be_checked()
            expect(enable_public_sharing).to_be_enabled()

            # Disable sharing
            enable_sharing_label.click()
            expect(enable_sharing).not_to_be_checked()
            expect(enable_public_sharing).not_to_be_checked()
            expect(enable_public_sharing).to_be_disabled()
