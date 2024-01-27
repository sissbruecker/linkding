from unittest.mock import patch, PropertyMock

from django.test import TestCase, modify_settings
from django.urls import reverse
from bookmarks.models import User
from bookmarks.middlewares import CustomRemoteUserMiddleware


class AuthProxySupportTest(TestCase):
    # Reproducing configuration from the settings logic here
    # ideally this test would just override the respective options
    @modify_settings(
        MIDDLEWARE={"append": "bookmarks.middlewares.CustomRemoteUserMiddleware"},
        AUTHENTICATION_BACKENDS={
            "prepend": "django.contrib.auth.backends.RemoteUserBackend"
        },
    )
    def test_auth_proxy_authentication(self):
        user = User.objects.create_user(
            "auth_proxy_user", "user@example.com", "password123"
        )

        headers = {"REMOTE_USER": user.username}
        response = self.client.get(reverse("bookmarks:index"), **headers)

        self.assertEqual(response.status_code, 200)

    # Reproducing configuration from the settings logic here
    # ideally this test would just override the respective options
    @modify_settings(
        MIDDLEWARE={"append": "bookmarks.middlewares.CustomRemoteUserMiddleware"},
        AUTHENTICATION_BACKENDS={
            "prepend": "django.contrib.auth.backends.RemoteUserBackend"
        },
    )
    def test_auth_proxy_with_custom_header(self):
        with patch.object(
            CustomRemoteUserMiddleware, "header", new_callable=PropertyMock
        ) as mock:
            mock.return_value = "Custom-User"
            user = User.objects.create_user(
                "auth_proxy_user", "user@example.com", "password123"
            )

            headers = {"Custom-User": user.username}
            response = self.client.get(reverse("bookmarks:index"), **headers)

            self.assertEqual(response.status_code, 200)

    def test_auth_proxy_is_disabled_by_default(self):
        user = User.objects.create_user(
            "auth_proxy_user", "user@example.com", "password123"
        )

        headers = {"REMOTE_USER": user.username}
        response = self.client.get(reverse("bookmarks:index"), **headers, follow=True)

        self.assertRedirects(response, "/login/?next=%2Fbookmarks")
