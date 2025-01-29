import importlib
import os

from django.test import TestCase, override_settings
from django.urls import URLResolver


class OidcSupportTest(TestCase):
    def test_should_not_add_oidc_urls_by_default(self):
        siteroot_urls = importlib.import_module("siteroot.urls")
        importlib.reload(siteroot_urls)
        oidc_url_found = any(
            isinstance(urlpattern, URLResolver) and urlpattern.pattern._route == "oidc/"
            for urlpattern in siteroot_urls.urlpatterns
        )

        self.assertFalse(oidc_url_found)

    @override_settings(LD_ENABLE_OIDC=True)
    def test_should_add_oidc_urls_when_enabled(self):
        siteroot_urls = importlib.import_module("siteroot.urls")
        importlib.reload(siteroot_urls)
        oidc_url_found = any(
            isinstance(urlpattern, URLResolver) and urlpattern.pattern._route == "oidc/"
            for urlpattern in siteroot_urls.urlpatterns
        )

        self.assertTrue(oidc_url_found)

    def test_should_not_add_oidc_authentication_backend_by_default(self):
        base_settings = importlib.import_module("siteroot.settings.base")
        importlib.reload(base_settings)

        self.assertListEqual(
            ["django.contrib.auth.backends.ModelBackend"],
            base_settings.AUTHENTICATION_BACKENDS,
        )

    def test_should_add_oidc_authentication_backend_when_enabled(self):
        os.environ["LD_ENABLE_OIDC"] = "True"
        base_settings = importlib.import_module("siteroot.settings.base")
        importlib.reload(base_settings)

        self.assertListEqual(
            [
                "django.contrib.auth.backends.ModelBackend",
                "mozilla_django_oidc.auth.OIDCAuthenticationBackend",
            ],
            base_settings.AUTHENTICATION_BACKENDS,
        )
        del os.environ["LD_ENABLE_OIDC"]  # Remove the temporary environment variable

    def test_default_settings(self):
        os.environ["LD_ENABLE_OIDC"] = "True"
        base_settings = importlib.import_module("siteroot.settings.base")
        importlib.reload(base_settings)

        self.assertEqual(
            True,
            base_settings.OIDC_VERIFY_SSL,
        )

        del os.environ["LD_ENABLE_OIDC"]

    def test_username_claim_email(self):
        os.environ["LD_ENABLE_OIDC"] = "True"
        base_settings = importlib.import_module("siteroot.settings.base")
        importlib.reload(base_settings)

        self.assertEqual(
            "email",
            base_settings.OIDC_USERNAME_CLAIM,
        )
        del os.environ["LD_ENABLE_OIDC"]

    @override_settings(LD_ENABLE_OIDC=True, OIDC_USERNAME_CLAIM="email")
    def test_username_should_be_email(self):
        email = "test@example.com"
        claims = {
            "email": "test@example.com",
            "name": "test",
            "given_name": "test",
            "preferred_username": "test",
            "nickname": "test",
            "groups": [],
        }
        from bookmarks import utils

        username = utils.generate_username(email, claims)

        self.assertEqual(
            email,
            username,
        )

    @override_settings(LD_ENABLE_OIDC=True, OIDC_USERNAME_CLAIM="preferred_username")
    def test_username_should_be_preferred_username(self):
        email = "test@example.com"
        claims = {
            "email": "test@example.com",
            "name": "test",
            "given_name": "test",
            "preferred_username": "test",
            "nickname": "test",
            "groups": [],
        }
        from bookmarks import utils

        username = utils.generate_username(email, claims)

        self.assertEqual(
            "test",
            username,
        )

    @override_settings(LD_ENABLE_OIDC=True, OIDC_USERNAME_CLAIM="nonexistant_claim")
    def test_username_fallback_to_email(self):
        email = "test@example.com"
        claims = {
            "email": "test@example.com",
            "name": "test",
            "given_name": "test",
            "preferred_username": "test",
            "nickname": "test",
            "groups": [],
        }
        from bookmarks import utils

        username = utils.generate_username(email, claims)

        self.assertEqual(
            email,
            username,
        )
