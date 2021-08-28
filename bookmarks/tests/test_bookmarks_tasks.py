from unittest.mock import patch

import waybackpy
from background_task.models import Task
from django.contrib.auth.models import User
from django.test import TestCase

from bookmarks.models import Bookmark
from bookmarks.services.tasks import create_web_archive_snapshot, schedule_bookmarks_without_snapshots
from bookmarks.tests.helpers import BookmarkFactoryMixin, disable_logging


class MockWaybackUrl:

    def __init__(self, archive_url: str):
        self.archive_url = archive_url

    def save(self):
        return self


class MockWaybackUrlWithSaveError:
    def save(self):
        raise NotImplementedError


class BookmarkTasksTestCase(TestCase, BookmarkFactoryMixin):

    @disable_logging
    def run_pending_task(self, task_function):
        func = getattr(task_function, 'task_function', None)
        task = Task.objects.all()[0]
        args, kwargs = task.params()
        func(*args, **kwargs)
        task.delete()

    @disable_logging
    def run_all_pending_tasks(self, task_function):
        func = getattr(task_function, 'task_function', None)
        tasks = Task.objects.all()

        for task in tasks:
            args, kwargs = task.params()
            func(*args, **kwargs)
            task.delete()

    def test_create_web_archive_snapshot_should_update_snapshot_url(self):
        bookmark = self.setup_bookmark()

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://example.com')):
            create_web_archive_snapshot(bookmark.id, False)
            self.run_pending_task(create_web_archive_snapshot)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

    def test_create_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://example.com')) as mock_wayback_url:
            create_web_archive_snapshot(123, False)
            self.run_pending_task(create_web_archive_snapshot)

            mock_wayback_url.assert_not_called()

    def test_create_web_archive_snapshot_should_handle_wayback_save_error(self):
        bookmark = self.setup_bookmark()

        with patch.object(waybackpy, 'Url',
                          return_value=MockWaybackUrlWithSaveError()):
            with self.assertRaises(NotImplementedError):
                create_web_archive_snapshot(bookmark.id, False)
                self.run_pending_task(create_web_archive_snapshot)

    def test_create_web_archive_snapshot_should_skip_if_snapshot_exists(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://other.com')):
            create_web_archive_snapshot(bookmark.id, False)
            self.run_pending_task(create_web_archive_snapshot)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

    def test_create_web_archive_snapshot_should_force_update_snapshot(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://other.com')):
            create_web_archive_snapshot(bookmark.id, True)
            self.run_pending_task(create_web_archive_snapshot)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, 'https://other.com')

    def test_schedule_bookmarks_without_snapshots_should_create_snapshot_task_for_all_bookmarks_without_snapshot(self):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://example.com')):
            schedule_bookmarks_without_snapshots(user.id)
            self.run_pending_task(schedule_bookmarks_without_snapshots)
            self.run_all_pending_tasks(create_web_archive_snapshot)

            for bookmark in Bookmark.objects.all():
                self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

    def test_schedule_bookmarks_without_snapshots_should_not_update_bookmarks_with_existing_snapshot(self):
        user = self.get_or_create_test_user()
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://other.com')):
            schedule_bookmarks_without_snapshots(user.id)
            self.run_pending_task(schedule_bookmarks_without_snapshots)
            self.run_all_pending_tasks(create_web_archive_snapshot)

            for bookmark in Bookmark.objects.all():
                self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

    def test_schedule_bookmarks_without_snapshots_should_only_update_user_owned_bookmarks(self):
        user = self.get_or_create_test_user()
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://example.com')):
            schedule_bookmarks_without_snapshots(user.id)
            self.run_pending_task(schedule_bookmarks_without_snapshots)
            self.run_all_pending_tasks(create_web_archive_snapshot)

            for bookmark in Bookmark.objects.all().filter(owner=user):
                self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

            for bookmark in Bookmark.objects.all().filter(owner=other_user):
                self.assertEqual(bookmark.web_archive_snapshot_url, '')
