from unittest.mock import patch

import waybackpy
from background_task.models import Task
from django.test import TestCase

from bookmarks.services.tasks import create_web_archive_snapshot
from bookmarks.tests.helpers import BookmarkFactoryMixin


class MockWaybackUrl:

    def __init__(self, archive_url: str):
        self.archive_url = archive_url

    def save(self):
        return self


class MockWaybackUrlWithSaveError:
    def save(self):
        raise NotImplementedError


class BookmarkTasksTestCase(TestCase, BookmarkFactoryMixin):

    def run_pending_task(self):
        func = getattr(create_web_archive_snapshot, 'task_function', None)
        task = Task.objects.all()[0]
        args, kwargs = task.params()
        func(*args, **kwargs)

    def test_create_web_archive_snapshot_should_update_snapshot_url(self):
        bookmark = self.setup_bookmark()

        with patch.object(waybackpy, 'Url',
                          return_value=MockWaybackUrl(
                              'https://web.archive.org/web/20210811214511/https://wanikani.com/')):
            create_web_archive_snapshot(bookmark.id)
            self.run_pending_task()
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url,
                             'https://web.archive.org/web/20210811214511/https://wanikani.com/')

    def test_create_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        with patch.object(waybackpy, 'Url',
                          return_value=MockWaybackUrl(
                              'https://web.archive.org/web/20210811214511/https://wanikani.com/')) as mock_wayback_url:
            create_web_archive_snapshot(123)
            self.run_pending_task()

            mock_wayback_url.assert_not_called()

    def test_create_web_archive_snapshot_should_handle_wayback_save_error(self):
        bookmark = self.setup_bookmark()

        with patch.object(waybackpy, 'Url',
                          return_value=MockWaybackUrlWithSaveError()):
            with self.assertRaises(NotImplementedError):
                create_web_archive_snapshot(bookmark.id)
                self.run_pending_task()
