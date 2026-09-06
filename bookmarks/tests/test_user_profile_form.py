from django.test import TestCase, override_settings

from bookmarks.forms import UserProfileForm
from bookmarks.tests.helpers import BookmarkFactoryMixin


class UserProfileFormLanguageTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()

    def form(self, language):
        data = {
            "theme": "auto",
            "bookmark_date_display": "relative",
            "bookmark_description_display": "inline",
            "bookmark_description_max_lines": 1,
            "bookmark_link_target": "_blank",
            "web_archive_integration": "disabled",
            "tag_search": "strict",
            "tag_grouping": "alphabetical",
            "items_per_page": 30,
            "language": language,
        }
        return UserProfileForm(data, instance=self.user.profile)

    @override_settings(LANGUAGES=[("en", "English"), ("de", "Deutsch")])
    def test_language_choices_contain_auto_and_all_languages(self):
        form = UserProfileForm(instance=self.user.profile)

        choices = list(form.fields["language"].choices)

        self.assertEqual([("", "Auto"), ("en", "English"), ("de", "Deutsch")], choices)

    def test_empty_language_is_valid_and_means_auto(self):
        form = self.form("")

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual("", self.user.profile.language)

    def test_known_language_is_saved(self):
        form = self.form("de")

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual("de", self.user.profile.language)

    def test_unknown_language_is_rejected(self):
        form = self.form("xx")

        self.assertFalse(form.is_valid())
        self.assertIn("language", form.errors)
