import datetime
from dataclasses import dataclass
from unittest import mock

import waybackpy
from background_task.models import Task
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from waybackpy.exceptions import WaybackError

import bookmarks.services.wayback
import bookmarks.services.favicon_loader
from bookmarks.models import UserProfile
from bookmarks.services import tasks
from bookmarks.tests.helpers import BookmarkFactoryMixin, disable_logging


class MockWaybackMachineSaveAPI:
    def __init__(self, archive_url: str = 'https://example.com/created_snapshot', fail_on_save: bool = False):
        self.archive_url = archive_url
        self.fail_on_save = fail_on_save

    def save(self):
        if self.fail_on_save:
            raise WaybackError
        return self


@dataclass
class MockCdxSnapshot:
    archive_url: str
    datetime_timestamp: datetime.datetime


class MockWaybackMachineCDXServerAPI:
    def __init__(self,
                 archive_url: str = 'https://example.com/newest_snapshot',
                 has_no_snapshot=False,
                 fail_loading_snapshot=False):
        self.archive_url = archive_url
        self.has_no_snapshot = has_no_snapshot
        self.fail_loading_snapshot = fail_loading_snapshot

    def newest(self):
        if self.has_no_snapshot:
            return None
        if self.fail_loading_snapshot:
            raise WaybackError
        return MockCdxSnapshot(self.archive_url, datetime.datetime.now())


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

        with mock.patch.object(waybackpy, 'WaybackMachineSaveAPI', return_value=MockWaybackMachineSaveAPI()):
            tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, 'https://example.com/created_snapshot')

    def test_create_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        with mock.patch.object(waybackpy, 'WaybackMachineSaveAPI',
                               return_value=MockWaybackMachineSaveAPI()) as mock_save_api:
            tasks._create_web_archive_snapshot_task(123, False)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)

            mock_save_api.assert_not_called()

    def test_create_web_archive_snapshot_should_skip_if_snapshot_exists(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with mock.patch.object(waybackpy, 'WaybackMachineSaveAPI',
                               return_value=MockWaybackMachineSaveAPI()) as mock_save_api:
            tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)

            mock_save_api.assert_not_called()

    def test_create_web_archive_snapshot_should_force_update_snapshot(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with mock.patch.object(waybackpy, 'WaybackMachineSaveAPI',
                               return_value=MockWaybackMachineSaveAPI('https://other.com')):
            tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, True)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, 'https://other.com')

    def test_create_web_archive_snapshot_should_use_newest_snapshot_as_fallback(self):
        bookmark = self.setup_bookmark()

        with mock.patch.object(waybackpy, 'WaybackMachineSaveAPI',
                               return_value=MockWaybackMachineSaveAPI(fail_on_save=True)):
            with mock.patch.object(bookmarks.services.wayback, 'CustomWaybackMachineCDXServerAPI',
                                   return_value=MockWaybackMachineCDXServerAPI()):
                tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)
                self.run_pending_task(tasks._create_web_archive_snapshot_task)

                bookmark.refresh_from_db()
                self.assertEqual('https://example.com/newest_snapshot', bookmark.web_archive_snapshot_url)

    def test_create_web_archive_snapshot_should_ignore_missing_newest_snapshot(self):
        bookmark = self.setup_bookmark()

        with mock.patch.object(waybackpy, 'WaybackMachineSaveAPI',
                               return_value=MockWaybackMachineSaveAPI(fail_on_save=True)):
            with mock.patch.object(bookmarks.services.wayback, 'CustomWaybackMachineCDXServerAPI',
                                   return_value=MockWaybackMachineCDXServerAPI(has_no_snapshot=True)):
                tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)
                self.run_pending_task(tasks._create_web_archive_snapshot_task)

                bookmark.refresh_from_db()
                self.assertEqual('', bookmark.web_archive_snapshot_url)

    def test_create_web_archive_snapshot_should_ignore_newest_snapshot_errors(self):
        bookmark = self.setup_bookmark()

        with mock.patch.object(waybackpy, 'WaybackMachineSaveAPI',
                               return_value=MockWaybackMachineSaveAPI(fail_on_save=True)):
            with mock.patch.object(bookmarks.services.wayback, 'CustomWaybackMachineCDXServerAPI',
                                   return_value=MockWaybackMachineCDXServerAPI(fail_loading_snapshot=True)):
                tasks.create_web_archive_snapshot(self.get_or_create_test_user(), bookmark, False)
                self.run_pending_task(tasks._create_web_archive_snapshot_task)

                bookmark.refresh_from_db()
                self.assertEqual('', bookmark.web_archive_snapshot_url)

    def test_load_web_archive_snapshot_should_update_snapshot_url(self):
        bookmark = self.setup_bookmark()

        with mock.patch.object(bookmarks.services.wayback, 'CustomWaybackMachineCDXServerAPI',
                               return_value=MockWaybackMachineCDXServerAPI()):
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            bookmark.refresh_from_db()
            self.assertEqual('https://example.com/newest_snapshot', bookmark.web_archive_snapshot_url)

    def test_load_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        with mock.patch.object(bookmarks.services.wayback, 'CustomWaybackMachineCDXServerAPI',
                               return_value=MockWaybackMachineCDXServerAPI()) as mock_cdx_api:
            tasks._load_web_archive_snapshot_task(123)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            mock_cdx_api.assert_not_called()

    def test_load_web_archive_snapshot_should_skip_if_snapshot_exists(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        with mock.patch.object(bookmarks.services.wayback, 'CustomWaybackMachineCDXServerAPI',
                               return_value=MockWaybackMachineCDXServerAPI()) as mock_cdx_api:
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            mock_cdx_api.assert_not_called()

    def test_load_web_archive_snapshot_should_handle_missing_snapshot(self):
        bookmark = self.setup_bookmark()

        with mock.patch.object(bookmarks.services.wayback, 'CustomWaybackMachineCDXServerAPI',
                               return_value=MockWaybackMachineCDXServerAPI(has_no_snapshot=True)):
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            self.assertEqual('', bookmark.web_archive_snapshot_url)

    def test_load_web_archive_snapshot_should_handle_wayback_errors(self):
        bookmark = self.setup_bookmark()

        with mock.patch.object(bookmarks.services.wayback, 'CustomWaybackMachineCDXServerAPI',
                               return_value=MockWaybackMachineCDXServerAPI(fail_loading_snapshot=True)):
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            self.assertEqual('', bookmark.web_archive_snapshot_url)

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

    def test_schedule_bookmarks_without_snapshots_should_load_snapshot_for_all_bookmarks_without_snapshot(self):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')
        self.setup_bookmark(web_archive_snapshot_url='https://example.com')

        tasks.schedule_bookmarks_without_snapshots(user)
        self.run_pending_task(tasks._schedule_bookmarks_without_snapshots_task)

        task_list = Task.objects.all()
        self.assertEqual(task_list.count(), 3)

        for task in task_list:
            self.assertEqual(task.task_name, 'bookmarks.services.tasks._load_web_archive_snapshot_task')

    def test_schedule_bookmarks_without_snapshots_should_only_update_user_owned_bookmarks(self):
        user = self.get_or_create_test_user()
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)

        tasks.schedule_bookmarks_without_snapshots(user)
        self.run_pending_task(tasks._schedule_bookmarks_without_snapshots_task)

        task_list = Task.objects.all()
        self.assertEqual(task_list.count(), 3)

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_schedule_bookmarks_without_snapshots_should_not_run_when_background_tasks_are_disabled(self):
        tasks.schedule_bookmarks_without_snapshots(self.user)

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_bookmarks_without_snapshots_should_not_run_when_web_archive_integration_is_disabled(self):
        self.user.profile.web_archive_integration = UserProfile.WEB_ARCHIVE_INTEGRATION_DISABLED
        self.user.profile.save()
        tasks.schedule_bookmarks_without_snapshots(self.user)

        self.assertEqual(Task.objects.count(), 0)

    def test_load_favicon_should_update_favicon_file(self):
        bookmark = self.setup_bookmark()

        with mock.patch('bookmarks.services.favicon_loader.load_favicon') as mock_load_favicon:
            mock_load_favicon.return_value = 'https_example_com.png'

            tasks.load_favicon(bookmark, False)
            self.run_pending_task(tasks._load_favicon_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.favicon_file, 'https_example_com.png')

    def test_load_favicon_should_handle_missing_bookmark(self):
        with mock.patch('bookmarks.services.favicon_loader.load_favicon') as mock_load_favicon:
            tasks._load_favicon_task(123, False)
            self.run_pending_task(tasks._load_favicon_task)

            mock_load_favicon.assert_not_called()

    def test_load_favicon_should_skip_if_favicon_exists(self):
        bookmark = self.setup_bookmark(favicon_file='https_example_com.png')

        with mock.patch('bookmarks.services.favicon_loader.load_favicon') as mock_load_favicon:
            tasks.load_favicon(bookmark, False)
            self.run_pending_task(tasks._load_favicon_task)

            mock_load_favicon.assert_not_called()

    def test_load_favicon_should_force_update_favicon(self):
        bookmark = self.setup_bookmark(favicon_file='https_example_com.png')

        with mock.patch('bookmarks.services.favicon_loader.load_favicon') as mock_load_favicon:
            mock_load_favicon.return_value = 'https_example_updated_com.png'
            tasks.load_favicon(bookmark, True)
            self.run_pending_task(tasks._load_favicon_task)

            mock_load_favicon.assert_called()

            bookmark.refresh_from_db()
            self.assertEqual(bookmark.favicon_file, 'https_example_updated_com.png')

    def test_schedule_bookmarks_without_favicons_should_load_favicon_for_all_bookmarks_without_favicon(self):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(favicon_file='https_example_com.png')
        self.setup_bookmark(favicon_file='https_example_com.png')
        self.setup_bookmark(favicon_file='https_example_com.png')

        tasks.schedule_bookmarks_without_favicons(user)
        self.run_pending_task(tasks._schedule_bookmarks_without_favicons_task)

        task_list = Task.objects.all()
        self.assertEqual(task_list.count(), 3)

        for task in task_list:
            self.assertEqual(task.task_name, 'bookmarks.services.tasks._load_favicon_task')

    def test_schedule_bookmarks_without_favicons_should_only_update_user_owned_bookmarks(self):
        user = self.get_or_create_test_user()
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)

        tasks.schedule_bookmarks_without_favicons(user)
        self.run_pending_task(tasks._schedule_bookmarks_without_favicons_task)

        task_list = Task.objects.all()
        self.assertEqual(task_list.count(), 3)
