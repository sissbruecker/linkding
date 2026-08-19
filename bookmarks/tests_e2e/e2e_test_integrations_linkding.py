import random
import re
import time

from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase

class IntegrationsLinkdingE2ETestCase(LinkdingE2ETestCase):
    def test_integrations_linkding(self):
        # NOTE (sentinal-fad8y): route(s) ['/settings/integrations/create-api-token'] are not in the Linkding
        # reverse() map — navigated via self.live_server_url + <path>.
        page = self.open(reverse("linkding:bookmarks.new"))
        expect(page).to_have_url(re.compile('/bookmarks/new'))
        page.goto(self.live_server_url + reverse("linkding:bookmarks.index"))
        expect(page).to_have_url(re.compile('/bookmarks'))
        page.goto(self.live_server_url + reverse("linkding:settings.integrations"))
        expect(page).to_have_url(re.compile('/settings/integrations'))
        page.goto(self.live_server_url + '/settings/integrations/create-api-token')
        expect(page).to_have_url(re.compile('/settings/integrations/create\\-api\\-token'))
        try:
            page.locator('#token-name').fill('QA Sentinal Record', timeout=5000)
        except Exception:
            pass
        page.get_by_role('button', name='Create Token', exact=True).click()
        expect(page).to_have_url(re.compile('/settings/integrations'))
        expect(page.locator('code').first).not_to_be_empty()
