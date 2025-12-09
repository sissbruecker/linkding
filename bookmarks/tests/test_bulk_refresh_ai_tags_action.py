from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from bookmarks.services import bookmarks
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BulkRefreshAITagsActionTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.client.force_login(self.user)

    @patch("bookmarks.views.bookmarks.refresh_ai_tags")
    def test_bulk_refresh_ai_tags(self, mock_refresh):
        mock_refresh.return_value = None
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()

        response = self.client.post(
            reverse("linkding:bookmarks.index.action"),
            {
                "bulk_action": ["bulk_refresh_ai_tags"],
                "bulk_execute": [""],
                "bookmark_id": [
                    str(bookmark1.id),
                    str(bookmark2.id),
                ],
            },
        )

        self.assertEqual(response.status_code, 302)
        mock_refresh.assert_called_once_with(
            [str(bookmark1.id), str(bookmark2.id)], self.user
        )

    @patch("bookmarks.services.bookmarks.tasks.auto_tag_bookmark")
    def test_bulk_refresh_ai_tags_integration(self, mock_task):
        # Test full integration from view to service to task
        # Need to mock at the task level to verify it propagates down

        # Enable AI auto-tagging for user (required for task scheduling)
        self.user.profile.ai_api_key = "sk-test"
        self.user.profile.ai_tag_vocabulary = "programming"
        self.user.profile.save()

        bookmark1 = self.setup_bookmark()

        self.client.post(
            reverse("linkding:bookmarks.index.action"),
            {
                "bulk_action": ["bulk_refresh_ai_tags"],
                "bulk_execute": [""],
                "bookmark_id": [str(bookmark1.id)],
            },
        )

        # Check if task scheduling was called
        # refresh_ai_tags -> tasks.auto_tag_bookmark -> _auto_tag_bookmark_task
        # We mocked auto_tag_bookmark in services.bookmarks
        # Wait, `refresh_ai_tags` calls `tasks.auto_tag_bookmark`
        mock_task.assert_called_once_with(self.user, bookmark1)
