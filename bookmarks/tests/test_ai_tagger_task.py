from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from bookmarks.models import Bookmark, Tag
from bookmarks.services.tasks import auto_tag_bookmark, _auto_tag_bookmark_task
from bookmarks.tests.helpers import BookmarkFactoryMixin

from huey.contrib.djhuey import HUEY as huey


class OpenAITaggerTaskTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        huey.immediate = True

        self.user = self.get_or_create_test_user()
        self.user.profile.ai_api_key = "sk-test"
        self.user.profile.ai_model = "gpt-5-nano"
        self.user.profile.ai_tag_vocabulary = "programming\npython"
        self.user.profile.save()
        self.bookmark = self.setup_bookmark(user=self.user)

    def tearDown(self):
        huey.immediate = False

    @patch("bookmarks.services.tasks._auto_tag_bookmark_task")
    def test_auto_tag_bookmark_schedule(self, mock_task):
        # Should schedule if enabled
        auto_tag_bookmark(self.user, self.bookmark)
        mock_task.assert_called_once_with(self.bookmark.id, self.user.id)

        # Should not schedule if user disabled
        mock_task.reset_mock()
        self.user.profile.ai_api_key = ""
        self.user.profile.save()
        auto_tag_bookmark(self.user, self.bookmark)
        mock_task.assert_not_called()

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    @patch("bookmarks.services.tasks._auto_tag_bookmark_task")
    def test_auto_tag_bookmark_schedule_disabled_tasks(self, mock_task):
        auto_tag_bookmark(self.user, self.bookmark)
        mock_task.assert_not_called()

    @patch("bookmarks.services.ai_auto_tagger.get_ai_tags")
    def test_task_applies_tags(self, mock_get_tags):
        mock_get_tags.return_value = ["programming", "python"]

        _auto_tag_bookmark_task(self.bookmark.id, self.user.id)

        self.bookmark.refresh_from_db()
        tags = list(self.bookmark.tags.values_list("name", flat=True))
        self.assertCountEqual(tags, ["programming", "python"])

    @patch("bookmarks.services.ai_auto_tagger.get_ai_tags")
    def test_task_skips_if_tags_exist(self, mock_get_tags):
        tag = self.setup_tag(name="manual", user=self.user)
        self.bookmark.tags.add(tag)

        _auto_tag_bookmark_task(self.bookmark.id, self.user.id)

        mock_get_tags.assert_not_called()

        self.bookmark.refresh_from_db()
        tags = list(self.bookmark.tags.values_list("name", flat=True))
        self.assertEqual(tags, ["manual"])

    @patch("bookmarks.services.ai_auto_tagger.get_ai_tags")
    def test_task_handles_empty_suggestions(self, mock_get_tags):
        mock_get_tags.return_value = []

        _auto_tag_bookmark_task(self.bookmark.id, self.user.id)

        self.bookmark.refresh_from_db()
        self.assertEqual(self.bookmark.tags.count(), 0)

    @patch("bookmarks.services.ai_auto_tagger.get_ai_tags")
    def test_task_handles_missing_objects(self, mock_get_tags):
        # Invalid bookmark ID
        _auto_tag_bookmark_task(99999, self.user.id)
        mock_get_tags.assert_not_called()

        # Invalid user ID
        _auto_tag_bookmark_task(self.bookmark.id, 99999)
        mock_get_tags.assert_not_called()

    @patch("bookmarks.services.ai_auto_tagger.get_ai_tags")
    def test_task_handles_exceptions(self, mock_get_tags):
        mock_get_tags.side_effect = Exception("Unexpected error")

        # Should not raise exception (logged only)
        _auto_tag_bookmark_task(self.bookmark.id, self.user.id)

        self.bookmark.refresh_from_db()
        self.assertEqual(self.bookmark.tags.count(), 0)
