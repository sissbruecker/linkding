from unittest.mock import patch

import waybackpy
from background_task.models import Task
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from bookmarks.models import Bookmark, UserProfile
from bookmarks.services import tasks
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

    def setUp(self):
        user = self.get_or_create_test_user()
        user.profile.web_archive_integration = UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED
        user.profile.save()

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
            tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

    def test_create_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://example.com')) as mock_wayback_url:
            tasks._create_web_archive_snapshot_task(123, False)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)

            mock_wayback_url.assert_not_called()

    def test_create_web_archive_snapshot_should_handle_wayback_save_error(self):
        bookmark = self.setup_bookmark()

        with patch.object(waybackpy, 'Url',
                          return_value=MockWaybackUrlWithSaveError()):
            with self.assertRaises(NotImplementedError):
                tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)
                self.run_pending_task(tasks._create_web_archive_snapshot_task)

    def test_create_web_archive_snapshot_should_skip_if_snapshot_exists(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://other.com')):
            tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

    def test_create_web_archive_snapshot_should_force_update_snapshot(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://other.com')):
            tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, True)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, 'https://other.com')

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_create_web_archive_snapshot_should_not_run_when_background_tasks_are_disabled(self):
        bookmark = self.setup_bookmark()
        tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)

        self.assertEqual(Task.objects.count(), 0)

    def test_create_web_archive_snapshot_should_not_run_when_web_archive_integration_is_disabled(self):
        self.user.profile.web_archive_integration = UserProfile.WEB_ARCHIVE_INTEGRATION_DISABLED
        self.user.profile.save()

        bookmark = self.setup_bookmark()
        tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_bookmarks_without_snapshots_should_create_snapshot_task_for_all_bookmarks_without_snapshot(self):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://example.com')):
            tasks.schedule_bookmarks_without_snapshots(user)
            self.run_pending_task(tasks._schedule_bookmarks_without_snapshots_task)
            self.run_all_pending_tasks(tasks._create_web_archive_snapshot_task)

            for bookmark in Bookmark.objects.all():
                self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

    def test_schedule_bookmarks_without_snapshots_should_not_update_bookmarks_with_existing_snapshot(self):
        user = self.get_or_create_test_user()
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with patch.object(waybackpy, 'Url', return_value=MockWaybackUrl('https://other.com')):
            tasks.schedule_bookmarks_without_snapshots(user)
            self.run_pending_task(tasks._schedule_bookmarks_without_snapshots_task)
            self.run_all_pending_tasks(tasks._create_web_archive_snapshot_task)

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
            tasks.schedule_bookmarks_without_snapshots(user)
            self.run_pending_task(tasks._schedule_bookmarks_without_snapshots_task)
            self.run_all_pending_tasks(tasks._create_web_archive_snapshot_task)

            for bookmark in Bookmark.objects.all().filter(owner=user):
                self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com')

            for bookmark in Bookmark.objects.all().filter(owner=other_user):
                self.assertEqual(bookmark.web_archive_snapshot_url, '')

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_schedule_bookmarks_without_snapshots_should_not_run_when_background_tasks_are_disabled(self):
        tasks.schedule_bookmarks_without_snapshots(self.user)

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_bookmarks_without_snapshots_should_not_run_when_web_archive_integration_is_disabled(self):
        self.user.profile.web_archive_integration = UserProfile.WEB_ARCHIVE_INTEGRATION_DISABLED
        self.user.profile.save()
        tasks.schedule_bookmarks_without_snapshots(self.user)

        self.assertEqual(Task.objects.count(), 0)
