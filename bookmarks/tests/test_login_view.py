from django.test import TestCase, override_settings
from django.urls import path, include

from bookmarks.tests.helpers import HtmlTestMixin
from siteroot.urls import urlpatterns as base_patterns

# Register OIDC urls for this test, otherwise login template can not render when OIDC is enabled
urlpatterns = base_patterns + [path("oidc/", include("mozilla_django_oidc.urls"))]


@override_settings(ROOT_URLCONF=__name__)
class LoginViewTestCase(TestCase, HtmlTestMixin):

    def test_should_not_show_oidc_login_by_default(self):
        response = self.client.get("/login/")
        soup = self.make_soup(response.content.decode())

        oidc_login_link = soup.find("a", text="Login with OIDC")

        self.assertIsNone(oidc_login_link)

    @override_settings(LD_ENABLE_OIDC=True)
    def test_should_show_oidc_login_when_enabled(self):
        response = self.client.get("/login/")
        soup = self.make_soup(response.content.decode())

        oidc_login_link = soup.find("a", text="Login with OIDC")

        self.assertIsNotNone(oidc_login_link)
