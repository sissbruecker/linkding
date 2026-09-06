import os
import tempfile

from django.test import SimpleTestCase

from bookmarks.i18n import discover_extra_languages


class DiscoverExtraLanguagesTestCase(SimpleTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.locale_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_language(self, code, filename="django.po"):
        messages_dir = os.path.join(self.locale_dir, code, "LC_MESSAGES")
        os.makedirs(messages_dir)
        with open(os.path.join(messages_dir, filename), "w") as f:
            f.write("")

    def test_returns_empty_list_for_missing_directory(self):
        result = discover_extra_languages(
            os.path.join(self.locale_dir, "does-not-exist"), ["en"]
        )
        self.assertEqual([], result)

    def test_returns_empty_list_for_empty_directory(self):
        result = discover_extra_languages(self.locale_dir, ["en"])
        self.assertEqual([], result)

    def test_returns_languages_with_po_or_mo_file(self):
        self.add_language("ja", "django.po")
        self.add_language("fr", "django.mo")

        result = discover_extra_languages(self.locale_dir, ["en"])

        self.assertEqual([("fr", "français"), ("ja", "日本語")], result)

    def test_skips_known_languages(self):
        self.add_language("de")
        self.add_language("ja")

        result = discover_extra_languages(self.locale_dir, ["en", "de"])

        self.assertEqual([("ja", "日本語")], result)

    def test_skips_directories_without_message_file(self):
        os.makedirs(os.path.join(self.locale_dir, "ja", "LC_MESSAGES"))
        os.makedirs(os.path.join(self.locale_dir, "fr"))

        result = discover_extra_languages(self.locale_dir, ["en"])

        self.assertEqual([], result)

    def test_uses_code_as_name_for_unknown_language(self):
        self.add_language("xx")

        result = discover_extra_languages(self.locale_dir, ["en"])

        self.assertEqual([("xx", "xx")], result)

    def test_normalizes_code_to_django_language_code(self):
        self.add_language("pt_BR")

        result = discover_extra_languages(self.locale_dir, ["en"])

        self.assertEqual([("pt-br", "Português Brasileiro")], result)
