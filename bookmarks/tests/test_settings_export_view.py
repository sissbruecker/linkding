import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark
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
        self.setup_bookmark(tags=[self.setup_tag()], is_archived=True)
        self.setup_bookmark(tags=[self.setup_tag()], is_archived=True)
        self.setup_bookmark(tags=[self.setup_tag()], is_archived=True)

        response = self.client.get(reverse("linkding:settings.export"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-type"], "text/plain; charset=UTF-8")

        for bookmark in Bookmark.objects.all():
            self.assertContains(response, bookmark.url)

    def test_should_only_export_user_bookmarks(self):
        other_user = self.setup_user()
        owned_bookmarks = [
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
        ]
        non_owned_bookmarks = [
            self.setup_bookmark(tags=[self.setup_tag()], user=other_user),
            self.setup_bookmark(tags=[self.setup_tag()], user=other_user),
            self.setup_bookmark(tags=[self.setup_tag()], user=other_user),
        ]

        response = self.client.get(reverse("linkding:settings.export"), follow=True)

        text = response.content.decode("utf-8")

        for bookmark in owned_bookmarks:
            self.assertIn(bookmark.url, text)

        for bookmark in non_owned_bookmarks:
            self.assertNotIn(bookmark.url, text)

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("linkding:settings.export"), follow=True)

        self.assertRedirects(
            response, reverse("login") + "?next=" + reverse("linkding:settings.export")
        )

    def test_should_show_hint_when_export_raises_error(self):
        with patch(
            "bookmarks.services.exporter.export_netscape_html"
        ) as mock_export_netscape_html:
            mock_export_netscape_html.side_effect = Exception("Nope")
            response = self.client.get(reverse("linkding:settings.export"), follow=True)

            self.assertTemplateUsed(response, "settings/general.html")
            self.assertFormErrorHint(
                response, "An error occurred during bookmark export."
            )

    def test_filename_includes_date_and_time(self):
        self.setup_bookmark()

        # Mock timezone.now to return a fixed datetime for predictable filename
        fixed_time = datetime.datetime(
            2023, 5, 15, 14, 30, 45, tzinfo=datetime.timezone.utc
        )

        with patch("bookmarks.views.settings.timezone.now", return_value=fixed_time):
            response = self.client.get(reverse("linkding:settings.export"), follow=True)

        self.assertEqual(response.status_code, 200)
        expected_filename = 'attachment; filename="bookmarks_2023-05-15_14-30-45.html"'
        self.assertEqual(response["Content-Disposition"], expected_filename)
