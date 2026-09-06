from django.test import TestCase, override_settings
from django.urls import reverse

from bookmarks.models import GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin


@override_settings(LANGUAGES=[("en", "English"), ("de", "Deutsch")])
class UserLanguageMiddlewareTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.client.force_login(self.user)

    def set_language(self, language):
        profile = self.user.profile
        profile.language = language
        profile.save()

    def test_uses_browser_language_when_profile_language_is_empty(self):
        self.set_language("")

        response = self.client.get(
            reverse("linkding:bookmarks.index"), headers={"accept-language": "de"}
        )

        self.assertEqual("de", response.wsgi_request.LANGUAGE_CODE)

    def test_falls_back_to_english_without_browser_language(self):
        self.set_language("")

        response = self.client.get(reverse("linkding:bookmarks.index"))

        # LANGUAGE_CODE is "en-us", but LANGUAGES only lists "en", so Django's
        # LocaleMiddleware resolves the generic variant
        self.assertEqual("en", response.wsgi_request.LANGUAGE_CODE)

    def test_profile_language_overrides_browser_language(self):
        self.set_language("de")

        response = self.client.get(
            reverse("linkding:bookmarks.index"), headers={"accept-language": "en"}
        )

        self.assertEqual("de", response.wsgi_request.LANGUAGE_CODE)

    def test_unknown_profile_language_is_ignored(self):
        self.set_language("xx")

        response = self.client.get(
            reverse("linkding:bookmarks.index"), headers={"accept-language": "en"}
        )

        self.assertEqual("en", response.wsgi_request.LANGUAGE_CODE)

    def test_guest_uses_guest_profile_language(self):
        self.client.logout()
        guest_user = self.setup_user()
        guest_profile = guest_user.profile
        guest_profile.language = "de"
        guest_profile.save()
        global_settings = GlobalSettings.get()
        global_settings.guest_profile_user = guest_user
        global_settings.save()

        response = self.client.get(reverse("login"), headers={"accept-language": "en"})

        self.assertEqual("de", response.wsgi_request.LANGUAGE_CODE)
