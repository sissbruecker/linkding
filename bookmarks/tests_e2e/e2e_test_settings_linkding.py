import random
import re
import time

from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase

class SettingsLinkdingE2ETestCase(LinkdingE2ETestCase):
    def test_settings_linkding(self):
        page = self.open(reverse("linkding:bookmarks.new"))
        expect(page).to_have_url(re.compile('/bookmarks/new'))
        page.goto(self.live_server_url + reverse("linkding:bookmarks.index"))
        expect(page).to_have_url(re.compile('/bookmarks'))
        page.goto(self.live_server_url + reverse("linkding:settings.general"))
        expect(page).to_have_url(re.compile('/settings/general'))
        try:
            page.locator('#id_bookmark_description_display').select_option('inline', timeout=5000)
        except Exception:
            pass
        _cb = page.locator('#import_map_private_flag')
        if _cb.count() and _cb.is_checked() != True:
            _lbl = _cb.locator('xpath=ancestor::label[1]')
            try:
                if _lbl.count():
                    _lbl.first.click(timeout=5000)
                else:
                    _cb.check(force=True, timeout=5000)
            except Exception:
                pass
        page.get_by_role('button', name='Upload', exact=True).click()
        expect(page).to_have_url(re.compile('/settings/general'))
