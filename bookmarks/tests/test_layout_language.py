from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class LayoutLanguageTestCase(TestCase, BookmarkFactoryMixin):
    def test_html_lang_attribute_follows_active_language(self):
        self.client.force_login(self.get_or_create_test_user())

        response = self.client.get(
            reverse("linkding:bookmarks.index"), headers={"accept-language": "de"}
        )

        self.assertContains(response, '<html lang="de"')

    def test_html_lang_attribute_defaults_to_english(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, '<html lang="en"')
