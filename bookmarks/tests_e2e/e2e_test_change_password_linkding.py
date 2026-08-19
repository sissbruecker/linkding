import random
import re
import time

from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase

class ChangePasswordLinkdingE2ETestCase(LinkdingE2ETestCase):
    def test_change_password_linkding(self):
        # NOTE (sentinal-fad8y): route(s) ['/change-password'] are not in the Linkding
        # reverse() map — navigated via self.live_server_url + <path>.
        page = self.open(reverse("linkding:bookmarks.new"))
        expect(page).to_have_url(re.compile('/bookmarks/new'))
        page.goto(self.live_server_url + reverse("linkding:bookmarks.index"))
        expect(page).to_have_url(re.compile('/bookmarks'))
        page.goto(self.live_server_url + reverse("linkding:settings.general"))
        expect(page).to_have_url(re.compile('/settings/general'))
        page.goto(self.live_server_url + '/change-password')
        expect(page).to_have_url(re.compile('/change\\-password'))
        page.get_by_role('button', name='Settings', exact=True).click()
        expect(page).to_have_url(re.compile('/change\\-password'))
