import hashlib
import random
from unittest.mock import patch, Mock

import requests
from django.test import TestCase, override_settings
from django.urls import reverse
from requests import RequestException

from bookmarks.models import UserProfile, GlobalSettings
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
            "update_profile": "",
            "theme": UserProfile.THEME_AUTO,
            "bookmark_date_display": UserProfile.BOOKMARK_DATE_DISPLAY_RELATIVE,
            "bookmark_description_display": UserProfile.BOOKMARK_DESCRIPTION_DISPLAY_INLINE,
            "bookmark_description_max_lines": 1,
            "bookmark_link_target": UserProfile.BOOKMARK_LINK_TARGET_BLANK,
            "web_archive_integration": UserProfile.WEB_ARCHIVE_INTEGRATION_DISABLED,
            "enable_sharing": False,
            "enable_public_sharing": False,
            "enable_favicons": False,
            "enable_preview_images": False,
            "enable_automatic_html_snapshots": True,
            "tag_search": UserProfile.TAG_SEARCH_STRICT,
            "tag_grouping": UserProfile.TAG_GROUPING_ALPHABETICAL,
            "display_url": False,
            "display_view_bookmark_action": True,
            "display_edit_bookmark_action": True,
            "display_archive_bookmark_action": True,
            "display_remove_bookmark_action": True,
            "permanent_notes": False,
            "custom_css": "",
            "auto_tagging_rules": "",
            "items_per_page": "30",
            "sticky_pagination": False,
        }

        return {**form_data, **overrides}

    def assertSuccessMessage(self, html, message: str, count=1):
        self.assertInHTML(
            f"""
            <div class="toast toast-success mb-4">{ message }</div>
        """,
            html,
            count=count,
        )

    def assertErrorMessage(self, html, message: str, count=1):
        self.assertInHTML(
            f"""
            <div class="toast toast-error mb-4">{ message }</div>
        """,
            html,
            count=count,
        )

    def test_should_render_successfully(self):
        response = self.client.get(reverse("bookmarks:settings.general"))

        self.assertEqual(response.status_code, 200)

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("bookmarks:settings.general"), follow=True)

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("bookmarks:settings.general"),
        )

        response = self.client.get(reverse("bookmarks:settings.update"), follow=True)

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("bookmarks:settings.update"),
        )

    def test_update_profile(self):
        form_data = {
            "update_profile": "",
            "theme": UserProfile.THEME_DARK,
            "bookmark_date_display": UserProfile.BOOKMARK_DATE_DISPLAY_HIDDEN,
            "bookmark_description_display": UserProfile.BOOKMARK_DESCRIPTION_DISPLAY_SEPARATE,
            "bookmark_description_max_lines": 3,
            "bookmark_link_target": UserProfile.BOOKMARK_LINK_TARGET_SELF,
            "web_archive_integration": UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED,
            "enable_sharing": True,
            "enable_public_sharing": True,
            "enable_favicons": True,
            "enable_preview_images": True,
            "enable_automatic_html_snapshots": False,
            "tag_search": UserProfile.TAG_SEARCH_LAX,
            "tag_grouping": UserProfile.TAG_GROUPING_DISABLED,
            "display_url": True,
            "display_view_bookmark_action": False,
            "display_edit_bookmark_action": False,
            "display_archive_bookmark_action": False,
            "display_remove_bookmark_action": False,
            "permanent_notes": True,
            "default_mark_unread": True,
            "custom_css": "body { background-color: #000; }",
            "auto_tagging_rules": "example.com tag",
            "items_per_page": "10",
            "sticky_pagination": True,
        }
        response = self.client.post(
            reverse("bookmarks:settings.update"), form_data, follow=True
        )
        html = response.content.decode()

        self.user.profile.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.profile.theme, form_data["theme"])
        self.assertEqual(
            self.user.profile.bookmark_date_display, form_data["bookmark_date_display"]
        )
        self.assertEqual(
            self.user.profile.bookmark_description_display,
            form_data["bookmark_description_display"],
        )
        self.assertEqual(
            self.user.profile.bookmark_description_max_lines,
            form_data["bookmark_description_max_lines"],
        )
        self.assertEqual(
            self.user.profile.bookmark_link_target, form_data["bookmark_link_target"]
        )
        self.assertEqual(
            self.user.profile.web_archive_integration,
            form_data["web_archive_integration"],
        )
        self.assertEqual(self.user.profile.enable_sharing, form_data["enable_sharing"])
        self.assertEqual(
            self.user.profile.enable_public_sharing, form_data["enable_public_sharing"]
        )
        self.assertEqual(
            self.user.profile.enable_favicons, form_data["enable_favicons"]
        )
        self.assertEqual(
            self.user.profile.enable_preview_images, form_data["enable_preview_images"]
        )
        self.assertEqual(
            self.user.profile.enable_automatic_html_snapshots,
            form_data["enable_automatic_html_snapshots"],
        )
        self.assertEqual(self.user.profile.tag_search, form_data["tag_search"])
        self.assertEqual(self.user.profile.tag_grouping, form_data["tag_grouping"])
        self.assertEqual(self.user.profile.display_url, form_data["display_url"])
        self.assertEqual(
            self.user.profile.display_view_bookmark_action,
            form_data["display_view_bookmark_action"],
        )
        self.assertEqual(
            self.user.profile.display_edit_bookmark_action,
            form_data["display_edit_bookmark_action"],
        )
        self.assertEqual(
            self.user.profile.display_archive_bookmark_action,
            form_data["display_archive_bookmark_action"],
        )
        self.assertEqual(
            self.user.profile.display_remove_bookmark_action,
            form_data["display_remove_bookmark_action"],
        )
        self.assertEqual(
            self.user.profile.permanent_notes, form_data["permanent_notes"]
        )
        self.assertEqual(
            self.user.profile.default_mark_unread, form_data["default_mark_unread"]
        )
        self.assertEqual(self.user.profile.custom_css, form_data["custom_css"])
        self.assertEqual(
            self.user.profile.auto_tagging_rules, form_data["auto_tagging_rules"]
        )
        self.assertEqual(
            self.user.profile.items_per_page, int(form_data["items_per_page"])
        )
        self.assertEqual(
            self.user.profile.sticky_pagination, form_data["sticky_pagination"]
        )

        self.assertSuccessMessage(html, "Profile updated")

    def test_update_profile_with_invalid_form_returns_422(self):
        form_data = self.create_profile_form_data({"items_per_page": "-1"})
        response = self.client.post(reverse("bookmarks:settings.update"), form_data)

        self.assertEqual(response.status_code, 422)

    def test_update_profile_should_not_be_called_without_respective_form_action(self):
        form_data = {
            "theme": UserProfile.THEME_DARK,
        }
        response = self.client.post(
            reverse("bookmarks:settings.update"), form_data, follow=True
        )
        html = response.content.decode()

        self.user.profile.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.profile.theme, UserProfile.THEME_AUTO)
        self.assertSuccessMessage(html, "Profile updated", count=0)

    def test_update_profile_updates_custom_css_hash(self):
        form_data = self.create_profile_form_data(
            {
                "custom_css": "body { background-color: #000; }",
            }
        )
        self.client.post(reverse("bookmarks:settings.update"), form_data, follow=True)
        self.user.profile.refresh_from_db()

        expected_hash = hashlib.md5(form_data["custom_css"].encode("utf-8")).hexdigest()
        self.assertEqual(expected_hash, self.user.profile.custom_css_hash)

        form_data["custom_css"] = "body { background-color: #fff; }"
        self.client.post(reverse("bookmarks:settings.update"), form_data, follow=True)
        self.user.profile.refresh_from_db()

        expected_hash = hashlib.md5(form_data["custom_css"].encode("utf-8")).hexdigest()
        self.assertEqual(expected_hash, self.user.profile.custom_css_hash)

        form_data["custom_css"] = ""
        self.client.post(reverse("bookmarks:settings.update"), form_data, follow=True)
        self.user.profile.refresh_from_db()

        self.assertEqual("", self.user.profile.custom_css_hash)

    def test_enable_favicons_should_schedule_icon_update(self):
        with patch.object(
            tasks, "schedule_bookmarks_without_favicons"
        ) as mock_schedule_bookmarks_without_favicons:
            # Enabling favicons schedules update
            form_data = self.create_profile_form_data(
                {
                    "enable_favicons": True,
                }
            )
            self.client.post(reverse("bookmarks:settings.update"), form_data)

            mock_schedule_bookmarks_without_favicons.assert_called_once_with(self.user)

            # No update scheduled if favicons are already enabled
            mock_schedule_bookmarks_without_favicons.reset_mock()

            self.client.post(reverse("bookmarks:settings.update"), form_data)

            mock_schedule_bookmarks_without_favicons.assert_not_called()

            # No update scheduled when disabling favicons
            form_data = self.create_profile_form_data(
                {
                    "enable_favicons": False,
                }
            )

            self.client.post(reverse("bookmarks:settings.update"), form_data)

            mock_schedule_bookmarks_without_favicons.assert_not_called()

    def test_refresh_favicons(self):
        with patch.object(
            tasks, "schedule_refresh_favicons"
        ) as mock_schedule_refresh_favicons:
            form_data = {
                "refresh_favicons": "",
            }
            response = self.client.post(
                reverse("bookmarks:settings.update"), form_data, follow=True
            )
            html = response.content.decode()

            mock_schedule_refresh_favicons.assert_called_once()
            self.assertSuccessMessage(
                html, "Scheduled favicon update. This may take a while..."
            )

    def test_refresh_favicons_should_not_be_called_without_respective_form_action(self):
        with patch.object(
            tasks, "schedule_refresh_favicons"
        ) as mock_schedule_refresh_favicons:
            form_data = {}
            response = self.client.post(reverse("bookmarks:settings.update"), form_data)
            html = response.content.decode()

            mock_schedule_refresh_favicons.assert_not_called()
            self.assertSuccessMessage(
                html, "Scheduled favicon update. This may take a while...", count=0
            )

    def test_refresh_favicons_should_be_visible_when_favicons_enabled_in_profile(self):
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = True
        profile.save()

        response = self.client.get(reverse("bookmarks:settings.general"))
        html = response.content.decode()

        self.assertInHTML(
            """
            <button class="btn mt-2" name="refresh_favicons">Refresh Favicons</button>
        """,
            html,
            count=1,
        )

    def test_refresh_favicons_should_not_be_visible_when_favicons_disabled_in_profile(
        self,
    ):
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = False
        profile.save()

        response = self.client.get(reverse("bookmarks:settings.general"))
        html = response.content.decode()

        self.assertInHTML(
            """
            <button class="btn mt-2" name="refresh_favicons">Refresh Favicons</button>
        """,
            html,
            count=0,
        )

    @override_settings(LD_ENABLE_REFRESH_FAVICONS=False)
    def test_refresh_favicons_should_not_be_visible_when_disabled(self):
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = True
        profile.save()

        response = self.client.get(reverse("bookmarks:settings.general"))
        html = response.content.decode()

        self.assertInHTML(
            """
            <button class="btn mt-2" name="refresh_favicons">Refresh Favicons</button>
        """,
            html,
            count=0,
        )

    def test_enable_preview_image_should_schedule_preview_update(self):
        with patch.object(
            tasks, "schedule_bookmarks_without_previews"
        ) as mock_schedule_bookmarks_without_previews:
            # Enabling favicons schedules update
            form_data = self.create_profile_form_data(
                {
                    "enable_preview_images": True,
                }
            )
            self.client.post(reverse("bookmarks:settings.update"), form_data)

            mock_schedule_bookmarks_without_previews.assert_called_once_with(self.user)

            # No update scheduled if favicons are already enabled
            mock_schedule_bookmarks_without_previews.reset_mock()

            self.client.post(reverse("bookmarks:settings.update"), form_data)

            mock_schedule_bookmarks_without_previews.assert_not_called()

            # No update scheduled when disabling favicons
            form_data = self.create_profile_form_data(
                {
                    "enable_preview_images": False,
                }
            )

            self.client.post(reverse("bookmarks:settings.update"), form_data)

            mock_schedule_bookmarks_without_previews.assert_not_called()

    def test_automatic_html_snapshots_should_be_hidden_when_snapshots_not_supported(
        self,
    ):
        response = self.client.get(reverse("bookmarks:settings.general"))
        html = response.content.decode()

        self.assertInHTML(
            """
            <input type="checkbox" name="enable_automatic_html_snapshots" id="id_enable_automatic_html_snapshots" checked="">
            """,
            html,
            count=0,
        )

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_automatic_html_snapshots_should_be_visible_when_snapshots_supported(
        self,
    ):
        response = self.client.get(reverse("bookmarks:settings.general"))
        html = response.content.decode()

        self.assertInHTML(
            """
            <input type="checkbox" name="enable_automatic_html_snapshots" id="id_enable_automatic_html_snapshots" checked="">
            """,
            html,
            count=1,
        )

    def test_about_shows_version_info(self):
        response = self.client.get(reverse("bookmarks:settings.general"))
        html = response.content.decode()

        self.assertInHTML(
            f"""
            <tr>
                <td>Version</td>
                <td>{get_version_info(random.random())}</td>
            </tr>
        """,
            html,
        )

    def test_get_version_info_just_displays_latest_when_versions_are_equal(self):
        latest_version_response_mock = Mock(
            status_code=200, json=lambda: {"name": f"v{app_version}"}
        )
        with patch.object(requests, "get", return_value=latest_version_response_mock):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, f"{app_version} (latest)")

    def test_get_version_info_shows_latest_version_when_versions_are_not_equal(self):
        latest_version_response_mock = Mock(
            status_code=200, json=lambda: {"name": f"v123.0.1"}
        )
        with patch.object(requests, "get", return_value=latest_version_response_mock):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, f"{app_version} (latest: 123.0.1)")

    def test_get_version_info_silently_ignores_request_errors(self):
        with patch.object(requests, "get", side_effect=RequestException()):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, f"{app_version}")

    def test_get_version_info_handles_invalid_response(self):
        latest_version_response_mock = Mock(status_code=403, json=lambda: {})
        with patch.object(requests, "get", return_value=latest_version_response_mock):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, app_version)

        latest_version_response_mock = Mock(status_code=200, json=lambda: {})
        with patch.object(requests, "get", return_value=latest_version_response_mock):
            version_info = get_version_info(random.random())
            self.assertEqual(version_info, app_version)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_missing_html_snapshots(self):
        with patch.object(
            tasks, "create_missing_html_snapshots"
        ) as mock_create_missing_html_snapshots:
            mock_create_missing_html_snapshots.return_value = 5
            form_data = {
                "create_missing_html_snapshots": "",
            }
            response = self.client.post(
                reverse("bookmarks:settings.update"), form_data, follow=True
            )
            html = response.content.decode()

            self.assertEqual(response.status_code, 200)
            mock_create_missing_html_snapshots.assert_called_once()
            self.assertSuccessMessage(
                html, "Queued 5 missing snapshots. This may take a while..."
            )

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_missing_html_snapshots_no_missing_snapshots(self):
        with patch.object(
            tasks, "create_missing_html_snapshots"
        ) as mock_create_missing_html_snapshots:
            mock_create_missing_html_snapshots.return_value = 0
            form_data = {
                "create_missing_html_snapshots": "",
            }
            response = self.client.post(
                reverse("bookmarks:settings.update"), form_data, follow=True
            )
            html = response.content.decode()

            self.assertEqual(response.status_code, 200)
            mock_create_missing_html_snapshots.assert_called_once()
            self.assertSuccessMessage(html, "No missing snapshots found.")

    def test_create_missing_html_snapshots_should_not_be_called_without_respective_form_action(
        self,
    ):
        with patch.object(
            tasks, "create_missing_html_snapshots"
        ) as mock_create_missing_html_snapshots:
            mock_create_missing_html_snapshots.return_value = 5
            form_data = {}
            response = self.client.post(
                reverse("bookmarks:settings.update"), form_data, follow=True
            )
            html = response.content.decode()

            self.assertEqual(response.status_code, 200)
            mock_create_missing_html_snapshots.assert_not_called()
            self.assertSuccessMessage(
                html, "Queued 5 missing snapshots. This may take a while...", count=0
            )

    def test_update_global_settings(self):
        superuser = self.setup_superuser()
        self.client.force_login(superuser)
        selectable_user = self.setup_user()

        # Update global settings
        form_data = {
            "update_global_settings": "",
            "landing_page": GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS,
            "guest_profile_user": selectable_user.id,
        }
        response = self.client.post(
            reverse("bookmarks:settings.update"), form_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertSuccessMessage(response.content.decode(), "Global settings updated")

        global_settings = GlobalSettings.get()
        self.assertEqual(global_settings.landing_page, form_data["landing_page"])
        self.assertEqual(global_settings.guest_profile_user, selectable_user)

        # Revert settings
        form_data = {
            "update_global_settings": "",
            "landing_page": GlobalSettings.LANDING_PAGE_LOGIN,
            "guest_profile_user": "",
        }
        response = self.client.post(
            reverse("bookmarks:settings.update"), form_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertSuccessMessage(response.content.decode(), "Global settings updated")

        global_settings = GlobalSettings.get()
        global_settings.refresh_from_db()
        self.assertEqual(global_settings.landing_page, form_data["landing_page"])
        self.assertIsNone(global_settings.guest_profile_user)

    def test_update_global_settings_should_not_be_called_without_respective_form_action(
        self,
    ):
        superuser = self.setup_superuser()
        self.client.force_login(superuser)

        form_data = {
            "landing_page": GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS,
        }
        response = self.client.post(
            reverse("bookmarks:settings.update"), form_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertSuccessMessage(
            response.content.decode(), "Global settings updated", count=0
        )

    def test_update_global_settings_checks_for_superuser(self):
        form_data = {
            "update_global_settings": "",
            "landing_page": GlobalSettings.LANDING_PAGE_SHARED_BOOKMARKS,
        }
        response = self.client.post(reverse("bookmarks:settings.update"), form_data)
        self.assertEqual(response.status_code, 403)

    def test_global_settings_only_visible_for_superuser(self):
        response = self.client.get(reverse("bookmarks:settings.general"))
        html = response.content.decode()

        self.assertInHTML(
            "<h2>Global settings</h2>",
            html,
            count=0,
        )

        superuser = self.setup_superuser()
        self.client.force_login(superuser)

        response = self.client.get(reverse("bookmarks:settings.general"))
        html = response.content.decode()

        self.assertInHTML(
            "<h2>Global settings</h2>",
            html,
            count=1,
        )
