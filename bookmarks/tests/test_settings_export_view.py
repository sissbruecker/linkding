from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class SettingsExportViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertFormErrorHint(self, response, text: str):
        self.assertContains(response, '<div class="has-error">')
        self.assertContains(response, text)

    def test_should_export_successfully(self):
        self.setup_bookmark(tags=[self.setup_tag()])
        self.setup_bookmark(tags=[self.setup_tag()])
        self.setup_bookmark(tags=[self.setup_tag()])

        response = self.client.get(
            reverse('bookmarks:settings.export'),
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'text/plain; charset=UTF-8')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="bookmarks.html"')

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('bookmarks:settings.export'), follow=True)

        self.assertRedirects(response, reverse('login') + '?next=' + reverse('bookmarks:settings.export'))

    def test_should_show_hint_when_export_raises_error(self):
        with patch('bookmarks.services.exporter.export_netscape_html') as mock_export_netscape_html:
            mock_export_netscape_html.side_effect = Exception('Nope')
            response = self.client.get(reverse('bookmarks:settings.export'), follow=True)

            self.assertTemplateUsed(response, 'settings/general.html')
            self.assertFormErrorHint(response, 'An error occurred during bookmark export.')
