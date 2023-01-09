import random
from unittest.mock import patch, Mock

import requests
from django.test import TestCase
from django.urls import reverse
from requests import RequestException

from bookmarks.models import UserProfile
from bookmarks.services import tasks
from bookmarks.tests.helpers import BookmarkFactoryMixin
from bookmarks.views.settings import app_version, get_version_info


class SettingsGeneralViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def create_profile_form_data(self, overrides=None):
        if not overrides:
            overrides = {}
        form_data = {
            'theme': UserProfile.THEME_AUTO,
            'bookmark_date_display': UserProfile.BOOKMARK_DATE_DISPLAY_RELATIVE,
            'bookmark_link_target': UserProfile.BOOKMARK_LINK_TARGET_BLANK,
            'web_archive_integration': UserProfile.WEB_ARCHIVE_INTEGRATION_DISABLED,
            'enable_sharing': False,
            'enable_favicons': False,
        }

        return {**form_data, **overrides}

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
            'web_archive_integration': UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED,
            'enable_sharing': True,
            'enable_favicons': True,
        }
        response = self.client.post(reverse('bookmarks:settings.general'), form_data)

        self.user.profile.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.profile.theme, form_data['theme'])
        self.assertEqual(self.user.profile.bookmark_date_display, form_data['bookmark_date_display'])
        self.assertEqual(self.user.profile.bookmark_link_target, form_data['bookmark_link_target'])
        self.assertEqual(self.user.profile.web_archive_integration, form_data['web_archive_integration'])
        self.assertEqual(self.user.profile.enable_sharing, form_data['enable_sharing'])
        self.assertEqual(self.user.profile.enable_favicons, form_data['enable_favicons'])

    def test_enable_favicons_schedules_icon_update(self):
        with patch.object(tasks, 'schedule_bookmarks_without_favicons') as mock_schedule_bookmarks_without_favicons:
            # Enabling favicons schedules update
            form_data = self.create_profile_form_data({
                'enable_favicons': True,
            })
            self.client.post(reverse('bookmarks:settings.general'), form_data)

            mock_schedule_bookmarks_without_favicons.assert_called_once_with(self.user)

            # No update scheduled if favicons are already enabled
            mock_schedule_bookmarks_without_favicons.reset_mock()

            self.client.post(reverse('bookmarks:settings.general'), form_data)

            mock_schedule_bookmarks_without_favicons.assert_not_called()

            # No update scheduled when disabling favicons
            form_data = self.create_profile_form_data({
                'enable_favicons': False,
            })

            self.client.post(reverse('bookmarks:settings.general'), form_data)

            mock_schedule_bookmarks_without_favicons.assert_not_called()

    def test_about_shows_version_info(self):
        response = self.client.get(reverse('bookmarks:settings.general'))
        html = response.content.decode()

        self.assertInHTML(f'''
            <tr>
                <td>Version</td>
                <td>{get_version_info(random.random())}</td>
            </tr>
        ''', html)

    def test_get_version_info_just_displays_latest_when_versions_are_equal(self):
        latest_version_response_mock = Mock(status_code=200, json=lambda: {'name': f'v{app_version}'})
        with patch.object(requests, 'get', return_value=latest_version_response_mock):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, f'{app_version} (latest)')

    def test_get_version_info_shows_latest_version_when_versions_are_not_equal(self):
        latest_version_response_mock = Mock(status_code=200, json=lambda: {'name': f'v123.0.1'})
        with patch.object(requests, 'get', return_value=latest_version_response_mock):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, f'{app_version} (latest: 123.0.1)')

    def test_get_version_info_silently_ignores_request_errors(self):
        with patch.object(requests, 'get', side_effect=RequestException()):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, f'{app_version}')

    def test_get_version_info_handles_invalid_response(self):
        latest_version_response_mock = Mock(status_code=403, json=lambda: {})
        with patch.object(requests, 'get', return_value=latest_version_response_mock):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, app_version)

        latest_version_response_mock = Mock(status_code=200, json=lambda: {})
        with patch.object(requests, 'get', return_value=latest_version_response_mock):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, app_version)
