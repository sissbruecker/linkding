from django.test import TestCase, override_settings
from django.urls import path, include

from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin
from siteroot.urls import urlpatterns as base_patterns

# Register OIDC urls for this test, otherwise login template can not render when OIDC is enabled
urlpatterns = base_patterns + [path("oidc/", include("mozilla_django_oidc.urls"))]


@override_settings(ROOT_URLCONF=__name__)
class LoginViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):

    def test_failed_login_should_return_401(self):
        response = self.client.post("/login/", {"username": "test", "password": "test"})
        self.assertEqual(response.status_code, 401)

    def test_successful_login_should_redirect(self):
        user = self.setup_user(name="test")
        user.set_password("test")
        user.save()

        response = self.client.post("/login/", {"username": "test", "password": "test"})
        self.assertEqual(response.status_code, 302)

    def test_should_not_show_oidc_login_by_default(self):
        response = self.client.get("/login/")
        soup = self.make_soup(response.content.decode())

        oidc_login_link = soup.find("a", string="Login with OIDC")

        self.assertIsNone(oidc_login_link)

    @override_settings(LD_ENABLE_OIDC=True)
    def test_should_show_oidc_login_when_enabled(self):
        response = self.client.get("/login/")
        soup = self.make_soup(response.content.decode())

        oidc_login_link = soup.find("a", string="Login with OIDC")

        self.assertIsNotNone(oidc_login_link)
