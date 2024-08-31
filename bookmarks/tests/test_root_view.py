from django.test import TestCase
from django.urls import reverse

from bookmarks.models import GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin


class RootViewTestCase(TestCase, BookmarkFactoryMixin):
    def test_unauthenticated_user_redirect_to_login_by_default(self):
        response = self.client.get(reverse("bookmarks:root"))
        self.assertRedirects(response, reverse("login"))

    def test_unauthenticated_redirect_to_shared_bookmarks_if_configured_in_global_settings(
        self,
    ):
        settings = GlobalSettings.get()
        settings.landing_page = GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS
        settings.save()

        response = self.client.get(reverse("bookmarks:root"))
        self.assertRedirects(response, reverse("bookmarks:shared"))

    def test_authenticated_user_always_redirected_to_bookmarks(self):
        self.client.force_login(self.get_or_create_test_user())

        response = self.client.get(reverse("bookmarks:root"))
        self.assertRedirects(response, reverse("bookmarks:index"))

        settings = GlobalSettings.get()
        settings.landing_page = GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS
        settings.save()

        response = self.client.get(reverse("bookmarks:root"))
        self.assertRedirects(response, reverse("bookmarks:index"))

        settings.landing_page = GlobalSettings.LANDING_PAGE_LOGIN
        settings.save()

        response = self.client.get(reverse("bookmarks:root"))
        self.assertRedirects(response, reverse("bookmarks:index"))
