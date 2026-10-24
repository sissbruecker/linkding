import datetime
import gettext
import re
from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import translation

from bookmarks.utils import humanize_absolute_date, humanize_relative_date


class CatalogTests(SimpleTestCase):
    def test_source_catalogs_have_no_fuzzy_or_corrupt_entries(self):
        root = (
            Path(settings.BASE_DIR) / "bookmarks" / "locale" / "zh_Hans" / "LC_MESSAGES"
        )
        for domain in ("django", "djangojs"):
            source = (root / f"{domain}.po").read_text(encoding="utf-8")
            self.assertNotRegex(source, r"(?m)^#,.*fuzzy")
            self.assertNotRegex(source, r"(?m)^msgstr(?:\[\d+\])? \"\?+\"$")
            self.assertNotIn("\ufffd", source)
            with (root / f"{domain}.mo").open("rb") as stream:
                catalog = gettext.GNUTranslations(stream)
            for key, value in catalog._catalog.items():
                if key:
                    self.assertTrue(value, repr(key))
                    self.assertNotRegex(value, r"^\s*\?+\s*$")

    def test_templates_compile_and_no_multiline_translate_tags(self):
        root = Path(settings.BASE_DIR) / "bookmarks" / "templates"
        for path in root.rglob("*.html"):
            with self.subTest(template=str(path)):
                get_template(path.relative_to(root).as_posix())
                source = path.read_text(encoding="utf-8")
                for match in re.finditer(
                    r"{%\s*(?:translate|trans)\s+.*?%}", source, re.S
                ):
                    self.assertNotIn("\n", match.group())

    def test_list_titles_follow_each_requests_language(self):
        from bookmarks.views.contexts import ActiveBookmarkListContext

        with translation.override("zh-hans"):
            self.assertEqual(str(ActiveBookmarkListContext.list_title), "书签")
        with translation.override("en"):
            self.assertEqual(str(ActiveBookmarkListContext.list_title), "Bookmarks")

    def test_settings_help_translates_at_runtime(self):
        with translation.override("zh-hans"):
            value = translation.gettext(
                "Whether to use a light or dark theme, or automatically adjust the theme based on your system's settings."
            )
            self.assertIn("主题", value)
            self.assertNotIn("Whether", value)

    def test_dates_translate_and_english_behavior_is_preserved(self):
        now = datetime.datetime(2026, 10, 24, tzinfo=datetime.UTC)
        with translation.override("zh-hans"):
            self.assertEqual(humanize_absolute_date(now, now), "今天")
            self.assertIn("年", humanize_relative_date(now.replace(year=2024), now))
        with translation.override("en"):
            self.assertEqual(humanize_absolute_date(now, now), "Today")
            self.assertEqual(
                humanize_relative_date(now.replace(year=2024), now), "2 years ago"
            )


class LanguageTests(TestCase):
    def tearDown(self):
        translation.deactivate()
        super().tearDown()

    def test_browser_language_and_cookie_switch(self):
        response = self.client.get(reverse("login"), HTTP_ACCEPT_LANGUAGE="zh-CN")
        self.assertContains(response, 'lang="zh-hans"')
        self.assertContains(response, "登录")
        self.assertNotContains(response, "{%")
        self.client.post(
            reverse("linkding:set_language"),
            {"language": "en", "next": reverse("login")},
        )
        response = self.client.get(reverse("login"), HTTP_ACCEPT_LANGUAGE="zh-CN")
        self.assertContains(response, 'lang="en"')

    def test_javascript_catalog(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "zh-hans"
        response = self.client.get(reverse("linkding:javascript_catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recent Searches")

    def test_token_modal_has_heading_and_quoted_default(self):
        with translation.override("en"):
            content = get_template("settings/create_api_token_modal.html").render({})
        self.assertIn('value="API Token"', content)
        self.assertIn("Create API token", content)
