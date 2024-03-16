from unittest.mock import patch

from django.test import TestCase

from bookmarks.services import tasks
from bookmarks.tests.helpers import BookmarkFactoryMixin


class SignalsTestCase(TestCase, BookmarkFactoryMixin):
    def test_login_should_schedule_snapshot_creation(self):
        user = self.get_or_create_test_user()

        with patch.object(
            tasks, "schedule_bookmarks_without_snapshots"
        ) as mock_schedule_bookmarks_without_snapshots:
            self.client.force_login(user)
            mock_schedule_bookmarks_without_snapshots.assert_called_once_with(user)
