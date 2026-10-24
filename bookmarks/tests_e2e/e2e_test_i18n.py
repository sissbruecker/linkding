from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class LanguageE2ETestCase(LinkdingE2ETestCase):
    def test_language_switch_updates_settings_and_javascript(self):
        page = self.open(reverse("linkding:settings.general"))
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.locator('select[name="language"]').select_option("zh-hans")
        page.locator('form[action$="set-language/"] button').click()
        expect(page.locator("html")).to_have_attribute("lang", "zh-hans")
        expect(page.get_by_text("选择浅色或深色主题，或根据系统设置自动调整主题。", exact=True)).to_be_visible()
        self.assertEqual(page.evaluate('window.gettext("Cancel")'), "取消")
        self.assertNotIn("{%", page.locator("body").inner_text())
        page.goto(self.live_server_url + reverse("linkding:settings.integrations"))
        expect(page.locator("html")).to_have_attribute("lang", "zh-hans")
        self.assertNotIn("{%", page.locator("body").inner_text())
        page.locator('select[name="language"]').select_option("en")
        page.locator('form[action$="set-language/"] button').click()
        expect(page.locator("html")).to_have_attribute("lang", "en")
        self.assertEqual(page.evaluate('window.gettext("Cancel")'), "Cancel")
        self.assertEqual(errors, [])
