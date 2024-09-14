from django.test import TestCase
from django.urls import reverse

from bookmarks.models import UserProfile, GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin
from bookmarks.middlewares import standard_profile


class LinkdingMiddlewareTestCase(TestCase, BookmarkFactoryMixin):
    def test_unauthenticated_user_should_use_standard_profile_by_default(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(standard_profile, response.wsgi_request.user_profile)

    def test_unauthenticated_user_should_use_custom_configured_profile(self):
        guest_user = self.setup_user()
        guest_user_profile = guest_user.profile
        guest_user_profile.theme = UserProfile.THEME_DARK
        guest_user_profile.save()

        global_settings = GlobalSettings.get()
        global_settings.guest_profile_user = guest_user
        global_settings.save()

        response = self.client.get(reverse("login"))

        self.assertEqual(guest_user_profile, response.wsgi_request.user_profile)

    def test_authenticated_user_should_use_own_profile(self):
        guest_user = self.setup_user()
        guest_user_profile = guest_user.profile
        guest_user_profile.theme = UserProfile.THEME_DARK
        guest_user_profile.save()

        global_settings = GlobalSettings.get()
        global_settings.guest_profile_user = guest_user
        global_settings.save()

        user = self.get_or_create_test_user()
        user_profile = user.profile
        user_profile.theme = UserProfile.THEME_LIGHT
        user_profile.save()
        self.client.force_login(user)

        response = self.client.get(reverse("login"), follow=True)

        self.assertEqual(user_profile, response.wsgi_request.user_profile)
