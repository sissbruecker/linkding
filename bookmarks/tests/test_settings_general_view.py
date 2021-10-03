from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin
from bookmarks.models import UserProfile


class SettingsGeneralViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_render_successfully(self):
        response = self.client.get(reverse('bookmarks:settings.general'))

        self.assertEqual(response.status_code, 200)

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('bookmarks:settings.general'), follow=True)

        self.assertRedirects(response, reverse('login') + '?next=' + reverse('bookmarks:settings.general'))

    def test_should_save_profile(self):
        form_data = {
            'theme': UserProfile.THEME_DARK,
            'bookmark_date_display': UserProfile.BOOKMARK_DATE_DISPLAY_HIDDEN,
            'bookmark_link_target': UserProfile.BOOKMARK_LINK_TARGET_SELF,
        }
        response = self.client.post(reverse('bookmarks:settings.general'), form_data)

        self.user.profile.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.profile.theme, form_data['theme'])
        self.assertEqual(self.user.profile.bookmark_date_display, form_data['bookmark_date_display'])
        self.assertEqual(self.user.profile.bookmark_link_target, form_data['bookmark_link_target'])
