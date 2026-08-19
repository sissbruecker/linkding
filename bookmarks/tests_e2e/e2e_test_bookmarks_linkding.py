import random
import re
import time

from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase

class BookmarksLinkdingE2ETestCase(LinkdingE2ETestCase):
    def test_bookmarks_linkding(self):
        _uniq = lambda: f"{int(time.time()*1000):x}{random.randint(0x1000, 0xffff):x}"
        page = self.open(reverse("linkding:bookmarks.new"))
        expect(page).to_have_url(re.compile('/bookmarks/new'))
        try:
            page.get_by_label('url').fill(f'https://example.com/qa-{_uniq()}', timeout=5000)
        except Exception:
            pass
        try:
            page.locator('#id_notes').fill('test', timeout=5000)
        except Exception:
            pass
        try:
            page.locator('#id_description').fill('test', timeout=5000)
        except Exception:
            pass
        try:
            page.locator('#id_tag_string').fill('test', timeout=5000)
        except Exception:
            pass
        _cb = page.locator('#id_shared')
        if _cb.count() and _cb.is_checked() != True:
            _lbl = _cb.locator('xpath=ancestor::label[1]')
            try:
                if _lbl.count():
                    _lbl.first.click(timeout=5000)
                else:
                    _cb.check(force=True, timeout=5000)
            except Exception:
                pass
        _cb = page.locator('#id_unread')
        if _cb.count() and _cb.is_checked() != True:
            _lbl = _cb.locator('xpath=ancestor::label[1]')
            try:
                if _lbl.count():
                    _lbl.first.click(timeout=5000)
                else:
                    _cb.check(force=True, timeout=5000)
            except Exception:
                pass
        page.get_by_role('button', name='Save', exact=True).click()
        expect(page).to_have_url(re.compile('/bookmarks'))
        expect(page.get_by_text('Example Domain').first).to_be_visible()
