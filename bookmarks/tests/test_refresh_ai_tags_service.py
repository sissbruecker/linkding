from unittest.mock import patch, MagicMock

from django.test import TestCase

from bookmarks.services.bookmarks import refresh_ai_tags
from bookmarks.tests.helpers import BookmarkFactoryMixin


class RefreshAITagsServiceTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.other_user = self.setup_user()

    @patch("bookmarks.services.tasks.auto_tag_bookmark")
    def test_refresh_ai_tags_updates_owned_bookmarks(self, mock_auto_tag):
        bookmark1 = self.setup_bookmark(user=self.user)
        bookmark2 = self.setup_bookmark(user=self.user)

        refresh_ai_tags([bookmark1.id, bookmark2.id], self.user)

        self.assertEqual(mock_auto_tag.call_count, 2)
        mock_auto_tag.assert_any_call(self.user, bookmark1)
        mock_auto_tag.assert_any_call(self.user, bookmark2)

    @patch("bookmarks.services.tasks.auto_tag_bookmark")
    def test_refresh_ai_tags_ignores_other_users_bookmarks(self, mock_auto_tag):
        bookmark1 = self.setup_bookmark(user=self.user)
        bookmark2 = self.setup_bookmark(user=self.other_user)

        refresh_ai_tags([bookmark1.id, bookmark2.id], self.user)

        # Should only call for bookmark1
        self.assertEqual(mock_auto_tag.call_count, 1)
        mock_auto_tag.assert_called_once_with(self.user, bookmark1)

    @patch("bookmarks.services.tasks.auto_tag_bookmark")
    def test_refresh_ai_tags_handles_mixed_id_types(self, mock_auto_tag):
        bookmark1 = self.setup_bookmark(user=self.user)
        bookmark2 = self.setup_bookmark(user=self.user)

        # Pass mixed int/str ids
        refresh_ai_tags([str(bookmark1.id), bookmark2.id], self.user)

        self.assertEqual(mock_auto_tag.call_count, 2)
