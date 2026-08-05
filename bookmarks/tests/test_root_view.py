from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse

from bookmarks.models import GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin


class RootViewTestCase(TestCase, BookmarkFactoryMixin):
    def assertRedirectsToLogin(self, response, next_url):
        # The root view redirects to the bookmarks page, which in turn
        # redirects unauthenticated users to the login page
        self.assertEqual(response.redirect_chain[0], (next_url, 302))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], "/login/")
        self.assertEqual(response.context["next"], next_url)

    def test_unauthenticated_user_redirect_to_login_by_default(self):
        response = self.client.get(reverse("linkding:root"), follow=True)
        self.assertRedirectsToLogin(response, reverse("linkding:bookmarks.index"))

    def test_unauthenticated_redirect_to_shared_bookmarks_if_configured_in_global_settings(
        self,
    ):
        settings = GlobalSettings.get()
        settings.landing_page = GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS
        settings.save()

        response = self.client.get(reverse("linkding:root"))
        self.assertRedirects(response, reverse("linkding:bookmarks.shared"))

    def test_authenticated_user_always_redirected_to_bookmarks(self):
        self.client.force_login(self.get_or_create_test_user())

        response = self.client.get(reverse("linkding:root"))
        self.assertRedirects(response, reverse("linkding:bookmarks.index"))

        settings = GlobalSettings.get()
        settings.landing_page = GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS
        settings.save()

        response = self.client.get(reverse("linkding:root"))
        self.assertRedirects(response, reverse("linkding:bookmarks.index"))

        settings.landing_page = GlobalSettings.LANDING_PAGE_LOGIN
        settings.save()

        response = self.client.get(reverse("linkding:root"))
        self.assertRedirects(response, reverse("linkding:bookmarks.index"))

    def test_authenticated_user_redirect_retains_query_string(self):
        self.client.force_login(self.get_or_create_test_user())

        query = urlencode({"q": "#china"})
        response = self.client.get(reverse("linkding:root") + "?" + query)
        self.assertRedirects(
            response, reverse("linkding:bookmarks.index") + "?" + query
        )

    def test_unauthenticated_shared_landing_redirect_retains_query_string(self):
        settings = GlobalSettings.get()
        settings.landing_page = GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS
        settings.save()

        query = urlencode({"q": "#china"})
        response = self.client.get(reverse("linkding:root") + "?" + query)
        self.assertRedirects(
            response, reverse("linkding:bookmarks.shared") + "?" + query
        )

    def test_unauthenticated_login_redirect_retains_query_string(self):
        query = urlencode({"q": "#china"})
        response = self.client.get(reverse("linkding:root") + "?" + query, follow=True)
        self.assertRedirectsToLogin(
            response, reverse("linkding:bookmarks.index") + "?" + query
        )
