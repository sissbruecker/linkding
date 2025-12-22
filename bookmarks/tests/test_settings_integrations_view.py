from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin
from bookmarks.models import ApiToken, FeedToken


class SettingsIntegrationsViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_render_successfully(self):
        response = self.client.get(reverse("linkding:settings.integrations"))

        self.assertEqual(response.status_code, 200)

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(
            reverse("linkding:settings.integrations"), follow=True
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("linkding:settings.integrations"),
        )

    def test_create_api_token(self):
        response = self.client.post(
            reverse("linkding:settings.integrations.create_api_token"),
            {"name": "My Test Token"},
        )

        self.assertRedirects(response, reverse("linkding:settings.integrations"))
        self.assertEqual(ApiToken.objects.count(), 1)
        token = ApiToken.objects.first()
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.name, "My Test Token")

    def test_create_api_token_with_empty_name(self):
        self.client.post(
            reverse("linkding:settings.integrations.create_api_token"),
            {"name": ""},
        )

        self.assertEqual(ApiToken.objects.count(), 1)
        token = ApiToken.objects.first()
        self.assertEqual(token.name, "API Token")

    def test_create_api_token_shows_key_once(self):
        self.client.post(
            reverse("linkding:settings.integrations.create_api_token"),
            {"name": "My Token"},
        )

        # First load should show the token
        response = self.client.get(reverse("linkding:settings.integrations"))
        token = ApiToken.objects.first()
        self.assertContains(response, token.key)

        # Second load should not show the token
        response = self.client.get(reverse("linkding:settings.integrations"))
        self.assertNotContains(response, token.key)

    def test_delete_api_token(self):
        token = self.setup_api_token(name="To Delete")

        response = self.client.post(
            reverse("linkding:settings.integrations.delete_api_token"),
            {"token_id": token.id},
        )

        self.assertRedirects(response, reverse("linkding:settings.integrations"))
        self.assertEqual(ApiToken.objects.count(), 0)

    def test_delete_api_token_wrong_user(self):
        other_user = self.setup_user(name="other")
        token = self.setup_api_token(user=other_user, name="Other's Token")

        response = self.client.post(
            reverse("linkding:settings.integrations.delete_api_token"),
            {"token_id": token.id},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(ApiToken.objects.count(), 1)

    def test_list_api_tokens(self):
        self.setup_api_token(name="Token 1")
        self.setup_api_token(name="Token 2")

        other_user = self.setup_user(name="other")
        self.setup_api_token(user=other_user, name="Other's Token")

        response = self.client.get(reverse("linkding:settings.integrations"))
        soup = self.make_soup(response.content.decode())

        section = soup.find("turbo-frame", id="api-section")
        table = section.find("table")
        rows = table.find_all("tr")

        self.assertEqual(len(rows), 3)

        first_row_cells = rows[1].find_all("td")
        self.assertEqual(first_row_cells[0].get_text(strip=True), "Token 2")
        self.assertIsNotNone(first_row_cells[1].get_text(strip=True))

        second_row_cells = rows[2].find_all("td")
        self.assertEqual(second_row_cells[0].get_text(strip=True), "Token 1")
        self.assertIsNotNone(second_row_cells[1].get_text(strip=True))

    def test_should_generate_feed_token_if_not_exists(self):
        self.assertEqual(FeedToken.objects.count(), 0)

        self.client.get(reverse("linkding:settings.integrations"))

        self.assertEqual(FeedToken.objects.count(), 1)
        token = FeedToken.objects.first()
        self.assertEqual(token.user, self.user)

    def test_should_not_generate_feed_token_if_exists(self):
        FeedToken.objects.get_or_create(user=self.user)
        self.assertEqual(FeedToken.objects.count(), 1)

        self.client.get(reverse("linkding:settings.integrations"))

        self.assertEqual(FeedToken.objects.count(), 1)

    def test_should_display_feed_urls(self):
        response = self.client.get(reverse("linkding:settings.integrations"))
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
