from django.contrib.staticfiles.testing import LiveServerTestCase
from playwright.sync_api import BrowserContext

from bookmarks.tests.helpers import BookmarkFactoryMixin


class LinkdingE2ETestCase(LiveServerTestCase, BookmarkFactoryMixin):
    def setUp(self) -> None:
        self.client.force_login(self.get_or_create_test_user())
        self.cookie = self.client.cookies['sessionid']

    def setup_browser(self, playwright) -> BrowserContext:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies([{
            'name': 'sessionid',
            'value': self.cookie.value,
            'domain': self.live_server_url.replace('http:', ''),
            'path': '/'
        }])
        return context
