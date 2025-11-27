from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from bookmarks.models import UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin


class OpenAISettingsViewTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.client.force_login(self.user)
        self.url = reverse("linkding:settings.update")

    def _get_base_form_data(self):
        return {
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
            "collapse_side_panel": False,
            "hide_bundles": False,
            "legacy_search": False,
        }

    def test_default_model_name(self):
        self.assertEqual(self.user.profile.openai_model, "gpt-5-nano")

    def test_update_profile_validates_openai_api_key_success(self):
        with patch(
            "bookmarks.services.openai_tagger.validate_api_key"
        ) as mock_validate:
            mock_validate.return_value = (True, None)

            form_data = self._get_base_form_data()
            form_data.update(
                {
                    "openai_api_key": "sk-valid-key",
                    "openai_model": "gpt-5-nano",
                    "openai_tag_vocabulary": "programming\npython",
                }
            )

            response = self.client.post(self.url, form_data)

            # Should redirect on success
            self.assertRedirects(response, reverse("linkding:settings.general"))

            # Check if data was saved
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.openai_api_key, "sk-valid-key")
            self.assertEqual(self.user.profile.openai_model, "gpt-5-nano")
            self.assertEqual(
                self.user.profile.openai_tag_vocabulary, "programming\npython"
            )

            mock_validate.assert_called_once_with("sk-valid-key")

    def test_update_profile_validates_openai_api_key_failure(self):
        with patch(
            "bookmarks.services.openai_tagger.validate_api_key"
        ) as mock_validate:
            mock_validate.return_value = (False, "Invalid API Key")

            form_data = self._get_base_form_data()
            form_data.update(
                {
                    "openai_api_key": "sk-invalid-key",
                    "openai_model": "gpt-5-nano",
                    "openai_tag_vocabulary": "programming\npython",
                }
            )

            response = self.client.post(self.url, form_data)

            # Should render error page (status 422)
            self.assertEqual(response.status_code, 422)

            # Check for error message
            self.assertContains(response, "Invalid API Key", status_code=422)

            # Check data was NOT saved
            self.user.profile.refresh_from_db()
            self.assertNotEqual(self.user.profile.openai_api_key, "sk-invalid-key")

    def test_update_profile_skips_validation_if_key_empty(self):
        with patch(
            "bookmarks.services.openai_tagger.validate_api_key"
        ) as mock_validate:
            form_data = self._get_base_form_data()
            form_data.update(
                {
                    "openai_api_key": "",
                    "openai_model": "gpt-5-nano",
                    "openai_tag_vocabulary": "",
                }
            )

            response = self.client.post(self.url, form_data)

            self.assertRedirects(response, reverse("linkding:settings.general"))
            mock_validate.assert_not_called()

            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.openai_api_key, "")
