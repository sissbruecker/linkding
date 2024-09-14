from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token

from bookmarks.tests.helpers import BookmarkFactoryMixin
from bookmarks.models import FeedToken


class SettingsIntegrationsViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_render_successfully(self):
        response = self.client.get(reverse("bookmarks:settings.integrations"))

        self.assertEqual(response.status_code, 200)

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(
            reverse("bookmarks:settings.integrations"), follow=True
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("bookmarks:settings.integrations"),
        )

    def test_should_generate_api_token_if_not_exists(self):
        self.assertEqual(Token.objects.count(), 0)

        self.client.get(reverse("bookmarks:settings.integrations"))

        self.assertEqual(Token.objects.count(), 1)
        token = Token.objects.first()
        self.assertEqual(token.user, self.user)

    def test_should_not_generate_api_token_if_exists(self):
        Token.objects.get_or_create(user=self.user)
        self.assertEqual(Token.objects.count(), 1)

        self.client.get(reverse("bookmarks:settings.integrations"))

        self.assertEqual(Token.objects.count(), 1)

    def test_should_generate_feed_token_if_not_exists(self):
        self.assertEqual(FeedToken.objects.count(), 0)

        self.client.get(reverse("bookmarks:settings.integrations"))

        self.assertEqual(FeedToken.objects.count(), 1)
        token = FeedToken.objects.first()
        self.assertEqual(token.user, self.user)

    def test_should_not_generate_feed_token_if_exists(self):
        FeedToken.objects.get_or_create(user=self.user)
        self.assertEqual(FeedToken.objects.count(), 1)

        self.client.get(reverse("bookmarks:settings.integrations"))

        self.assertEqual(FeedToken.objects.count(), 1)

    def test_should_display_feed_urls(self):
        response = self.client.get(reverse("bookmarks:settings.integrations"))
        html = response.content.decode()

        token = FeedToken.objects.first()
        self.assertInHTML(
            f'<a target="_blank" href="http://testserver/feeds/{token.key}/all">All bookmarks</a>',
            html,
        )
        self.assertInHTML(
            f'<a target="_blank" href="http://testserver/feeds/{token.key}/unread">Unread bookmarks</a>',
            html,
        )
        self.assertInHTML(
            f'<a target="_blank" href="http://testserver/feeds/{token.key}/shared">Shared bookmarks</a>',
            html,
        )
        self.assertInHTML(
            '<a target="_blank" href="http://testserver/feeds/shared">Public shared bookmarks</a>',
            html,
        )
