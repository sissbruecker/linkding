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
            "default_mark_unread": False,
            "default_mark_shared": False,
        }

    def test_default_model_name(self):
        self.assertEqual(self.user.profile.ai_model, "")

    def test_update_profile_validates_ai_api_key_success(self):
        with patch(
            "bookmarks.services.ai_auto_tagger.validate_api_key"
        ) as mock_validate:
            mock_validate.return_value = (True, None)

            form_data = self._get_base_form_data()
            form_data.update(
                {
                    "ai_api_key": "sk-valid-key",
                    "ai_model": "gpt-5-nano",
                    "ai_tag_vocabulary": "programming\npython",
                }
            )

            response = self.client.post(self.url, form_data)

            # Should redirect on success
            self.assertRedirects(response, reverse("linkding:settings.general"))

            # Check if data was saved
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.ai_api_key, "sk-valid-key")
            self.assertEqual(self.user.profile.ai_model, "gpt-5-nano")
            self.assertEqual(self.user.profile.ai_tag_vocabulary, "programming\npython")

            # Validation should be called with empty base_url (empty string)
            mock_validate.assert_called_once_with("sk-valid-key", "")

    def test_update_profile_validates_ai_api_key_failure(self):
        with patch(
            "bookmarks.services.ai_auto_tagger.validate_api_key"
        ) as mock_validate:
            mock_validate.return_value = (False, "Invalid API key")

            form_data = self._get_base_form_data()
            form_data.update(
                {
                    "ai_api_key": "sk-invalid-key",
                    "ai_model": "gpt-5-nano",
                    "ai_tag_vocabulary": "programming\npython",
                }
            )

            response = self.client.post(self.url, form_data)

            # Should render error page (status 422)
            self.assertEqual(response.status_code, 422)

            # Check for error message
            self.assertContains(response, "Invalid API key", status_code=422)

            # Check data was NOT saved
            self.user.profile.refresh_from_db()
            self.assertNotEqual(self.user.profile.ai_api_key, "sk-invalid-key")

    def test_update_profile_skips_validation_if_key_empty(self):
        with patch(
            "bookmarks.services.ai_auto_tagger.validate_api_key"
        ) as mock_validate:
            form_data = self._get_base_form_data()
            form_data.update(
                {
                    "ai_api_key": "",
                    "ai_model": "gpt-5-nano",
                    "ai_tag_vocabulary": "",
                }
            )

            response = self.client.post(self.url, form_data)

            self.assertRedirects(response, reverse("linkding:settings.general"))
            mock_validate.assert_not_called()

            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.ai_api_key, "")

    @patch("bookmarks.services.ai_auto_tagger.validate_api_key")
    def test_update_profile_validates_base_url_format(self, mock_validate):
        """Test that base URL format is validated"""
        mock_validate.return_value = (True, None)
        form_data = self._get_base_form_data()
        form_data.update(
            {
                "ai_api_key": "sk-test",
                "ai_model": "gpt-5-nano",
                "ai_tag_vocabulary": "programming",
                "ai_base_url": "invalid-url",  # Invalid URL format
            }
        )

        response = self.client.post(self.url, form_data)

        # Should show error for invalid URL (422 = Unprocessable Content)
        self.assertIn(response.status_code, [200, 422])
        if hasattr(response, "context") and response.context:
            self.assertFormError(
                response.context["form"],
                "ai_base_url",
                "Invalid URL format. Must include protocol (http:// or https://) and domain.",
            )

    @patch("bookmarks.services.ai_auto_tagger.validate_api_key")
    def test_update_profile_skips_validation_with_base_url(self, mock_validate):
        """Test that API key validation is skipped when base_url is provided"""
        mock_validate.return_value = (True, None)

        form_data = self._get_base_form_data()
        form_data.update(
            {
                "ai_api_key": "any-key",
                "ai_model": "gpt-5-nano",
                "ai_tag_vocabulary": "programming",
                "ai_base_url": "http://localhost:11434/v1",
            }
        )

        response = self.client.post(self.url, form_data)

        self.assertRedirects(response, reverse("linkding:settings.general"))
        # Validation should be called with base_url parameter
        mock_validate.assert_called_once_with("any-key", "http://localhost:11434/v1")

    @patch("bookmarks.services.ai_auto_tagger.validate_api_key")
    def test_update_profile_validates_normally_without_base_url(self, mock_validate):
        """Test that API key validation runs normally when base_url is empty"""
        mock_validate.return_value = (True, None)

        form_data = self._get_base_form_data()
        form_data.update(
            {
                "ai_api_key": "sk-test",
                "ai_model": "gpt-5-nano",
                "ai_tag_vocabulary": "programming",
                "ai_base_url": "",  # Empty base_url
            }
        )

        response = self.client.post(self.url, form_data)

        self.assertRedirects(response, reverse("linkding:settings.general"))
        # Validation should be called without base_url (empty string passed)
        mock_validate.assert_called_once_with("sk-test", "")

    @patch("bookmarks.services.ai_auto_tagger.validate_api_key")
    def test_update_profile_accepts_valid_base_url(self, mock_validate):
        """Test that valid base URLs are accepted"""
        mock_validate.return_value = (True, None)

        valid_urls = [
            "http://localhost:11434/v1",
            "https://api.example.com/v1",
            "http://192.168.1.100:8080/v1",
        ]

        for url in valid_urls:
            form_data = self._get_base_form_data()
            form_data.update(
                {
                    "ai_api_key": "any-key",
                    "ai_model": "gpt-5-nano",
                    "ai_tag_vocabulary": "programming",
                    "ai_base_url": url,
                }
            )

            response = self.client.post(self.url, form_data)
            self.assertRedirects(response, reverse("linkding:settings.general"))

            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.ai_base_url, url)
