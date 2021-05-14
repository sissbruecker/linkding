from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token

from bookmarks.tests.helpers import BookmarkFactoryMixin


class SettingsApiViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_render_successfully(self):
        response = self.client.get(reverse('bookmarks:settings.api'))

        self.assertEqual(response.status_code, 200)

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('bookmarks:settings.api'), follow=True)

        self.assertRedirects(response, reverse('login') + '?next=' + reverse('bookmarks:settings.api'))

    def test_should_generate_api_token_if_not_exists(self):
        self.assertEqual(Token.objects.count(), 0)

        self.client.get(reverse('bookmarks:settings.api'))

        self.assertEqual(Token.objects.count(), 1)
        token = Token.objects.first()
        self.assertEqual(token.user, self.user)

    def test_should_not_generate_api_token_if_exists(self):
        Token.objects.get_or_create(user=self.user)
        self.assertEqual(Token.objects.count(), 1)

        self.client.get(reverse('bookmarks:settings.api'))

        self.assertEqual(Token.objects.count(), 1)
