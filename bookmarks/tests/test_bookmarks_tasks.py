import datetime
import os.path
from dataclasses import dataclass
from typing import Any
from unittest import mock

import waybackpy
from background_task.models import Task
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from waybackpy.exceptions import WaybackError

import bookmarks.services.favicon_loader
import bookmarks.services.wayback
from bookmarks.models import BookmarkAsset, UserProfile
from bookmarks.services import tasks, singlefile
from bookmarks.tests.helpers import BookmarkFactoryMixin, disable_logging


def create_wayback_machine_save_api_mock(
    archive_url: str = "https://example.com/created_snapshot",
    fail_on_save: bool = False,
):
    mock_api = mock.Mock(archive_url=archive_url)

    if fail_on_save:
        mock_api.save.side_effect = WaybackError

    return mock_api


@dataclass
class MockCdxSnapshot:
    archive_url: str
    datetime_timestamp: datetime.datetime


def create_cdx_server_api_mock(
    archive_url: str | None = "https://example.com/newest_snapshot",
    fail_loading_snapshot=False,
):
    mock_api = mock.Mock()

    if fail_loading_snapshot:
        mock_api.newest.side_effect = WaybackError
    elif archive_url:
        mock_api.newest.return_value = MockCdxSnapshot(
            archive_url, datetime.datetime.now()
        )
    else:
        mock_api.newest.return_value = None

    return mock_api


class BookmarkTasksTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self):
        user = self.get_or_create_test_user()
        user.profile.web_archive_integration = (
            UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED
        )
        user.profile.enable_favicons = True
        user.profile.save()

    @disable_logging
    def run_pending_task(self, task_function: Any):
        func = getattr(task_function, "task_function", None)
        task = Task.objects.all()[0]
        self.assertEqual(task_function.name, task.task_name)
        args, kwargs = task.params()
        func(*args, **kwargs)
        task.delete()

    @disable_logging
    def run_all_pending_tasks(self, task_function: Any):
        func = getattr(task_function, "task_function", None)
        tasks = Task.objects.all()

        for task in tasks:
            self.assertEqual(task_function.name, task.task_name)
            args, kwargs = task.params()
            func(*args, **kwargs)
            task.delete()

    def test_create_web_archive_snapshot_should_update_snapshot_url(self):
        bookmark = self.setup_bookmark()
        mock_save_api = create_wayback_machine_save_api_mock()

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=mock_save_api
        ):
            tasks.create_web_archive_snapshot(
                self.get_or_create_test_user(), bookmark, False
            )
            self.run_pending_task(tasks._create_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            mock_save_api.save.assert_called_once()
            self.assertEqual(
                bookmark.web_archive_snapshot_url,
                "https://example.com/created_snapshot",
            )

    def test_create_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        mock_save_api = create_wayback_machine_save_api_mock()

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=mock_save_api
        ):
            tasks._create_web_archive_snapshot_task(123, False)
            self.run_pending_task(tasks._create_web_archive_snapshot_task)

            mock_save_api.save.assert_not_called()

    def test_create_web_archive_snapshot_should_skip_if_snapshot_exists(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com")
        mock_save_api = create_wayback_machine_save_api_mock()

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=mock_save_api
        ):
            tasks.create_web_archive_snapshot(
                self.get_or_create_test_user(), bookmark, False
            )
            self.run_pending_task(tasks._create_web_archive_snapshot_task)

            mock_save_api.assert_not_called()

    def test_create_web_archive_snapshot_should_force_update_snapshot(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com")
        mock_save_api = create_wayback_machine_save_api_mock(
            archive_url="https://other.com"
        )

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=mock_save_api
        ):
            tasks.create_web_archive_snapshot(
                self.get_or_create_test_user(), bookmark, True
            )
            self.run_pending_task(tasks._create_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.web_archive_snapshot_url, "https://other.com")

    def test_create_web_archive_snapshot_should_use_newest_snapshot_as_fallback(self):
        bookmark = self.setup_bookmark()
        mock_save_api = create_wayback_machine_save_api_mock(fail_on_save=True)
        mock_cdx_api = create_cdx_server_api_mock()

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=mock_save_api
        ):
            with mock.patch.object(
                bookmarks.services.wayback,
                "CustomWaybackMachineCDXServerAPI",
                return_value=mock_cdx_api,
            ):
                tasks.create_web_archive_snapshot(
                    self.get_or_create_test_user(), bookmark, False
                )
                self.run_pending_task(tasks._create_web_archive_snapshot_task)

                bookmark.refresh_from_db()
                mock_cdx_api.newest.assert_called_once()
                self.assertEqual(
                    "https://example.com/newest_snapshot",
                    bookmark.web_archive_snapshot_url,
                )

    def test_create_web_archive_snapshot_should_ignore_missing_newest_snapshot(self):
        bookmark = self.setup_bookmark()
        mock_save_api = create_wayback_machine_save_api_mock(fail_on_save=True)
        mock_cdx_api = create_cdx_server_api_mock(archive_url=None)

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=mock_save_api
        ):
            with mock.patch.object(
                bookmarks.services.wayback,
                "CustomWaybackMachineCDXServerAPI",
                return_value=mock_cdx_api,
            ):
                tasks.create_web_archive_snapshot(
                    self.get_or_create_test_user(), bookmark, False
                )
                self.run_pending_task(tasks._create_web_archive_snapshot_task)

                bookmark.refresh_from_db()
                self.assertEqual("", bookmark.web_archive_snapshot_url)

    def test_create_web_archive_snapshot_should_ignore_newest_snapshot_errors(self):
        bookmark = self.setup_bookmark()
        mock_save_api = create_wayback_machine_save_api_mock(fail_on_save=True)
        mock_cdx_api = create_cdx_server_api_mock(fail_loading_snapshot=True)

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=mock_save_api
        ):
            with mock.patch.object(
                bookmarks.services.wayback,
                "CustomWaybackMachineCDXServerAPI",
                return_value=mock_cdx_api,
            ):
                tasks.create_web_archive_snapshot(
                    self.get_or_create_test_user(), bookmark, False
                )
                self.run_pending_task(tasks._create_web_archive_snapshot_task)

                bookmark.refresh_from_db()
                self.assertEqual("", bookmark.web_archive_snapshot_url)

    def test_create_web_archive_snapshot_should_not_save_stale_bookmark_data(self):
        bookmark = self.setup_bookmark()
        mock_save_api = create_wayback_machine_save_api_mock()

        # update bookmark during API call to check that saving
        # the snapshot does not overwrite updated bookmark data
        def mock_save_impl():
            bookmark.title = "Updated title"
            bookmark.save()

        mock_save_api.save.side_effect = mock_save_impl

        with mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=mock_save_api
        ):
            tasks.create_web_archive_snapshot(
                self.get_or_create_test_user(), bookmark, False
            )
            self.run_pending_task(tasks._create_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.title, "Updated title")
            self.assertEqual(
                "https://example.com/created_snapshot",
                bookmark.web_archive_snapshot_url,
            )

    def test_load_web_archive_snapshot_should_update_snapshot_url(self):
        bookmark = self.setup_bookmark()
        mock_cdx_api = create_cdx_server_api_mock()

        with mock.patch.object(
            bookmarks.services.wayback,
            "CustomWaybackMachineCDXServerAPI",
            return_value=mock_cdx_api,
        ):
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            bookmark.refresh_from_db()
            mock_cdx_api.newest.assert_called_once()
            self.assertEqual(
                "https://example.com/newest_snapshot", bookmark.web_archive_snapshot_url
            )

    def test_load_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        mock_cdx_api = create_cdx_server_api_mock()

        with mock.patch.object(
            bookmarks.services.wayback,
            "CustomWaybackMachineCDXServerAPI",
            return_value=mock_cdx_api,
        ):
            tasks._load_web_archive_snapshot_task(123)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            mock_cdx_api.newest.assert_not_called()

    def test_load_web_archive_snapshot_should_skip_if_snapshot_exists(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com")
        mock_cdx_api = create_cdx_server_api_mock()

        with mock.patch.object(
            bookmarks.services.wayback,
            "CustomWaybackMachineCDXServerAPI",
            return_value=mock_cdx_api,
        ):
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            mock_cdx_api.newest.assert_not_called()

    def test_load_web_archive_snapshot_should_handle_missing_snapshot(self):
        bookmark = self.setup_bookmark()
        mock_cdx_api = create_cdx_server_api_mock(archive_url=None)

        with mock.patch.object(
            bookmarks.services.wayback,
            "CustomWaybackMachineCDXServerAPI",
            return_value=mock_cdx_api,
        ):
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            self.assertEqual("", bookmark.web_archive_snapshot_url)

    def test_load_web_archive_snapshot_should_handle_wayback_errors(self):
        bookmark = self.setup_bookmark()
        mock_cdx_api = create_cdx_server_api_mock(fail_loading_snapshot=True)

        with mock.patch.object(
            bookmarks.services.wayback,
            "CustomWaybackMachineCDXServerAPI",
            return_value=mock_cdx_api,
        ):
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)

            self.assertEqual("", bookmark.web_archive_snapshot_url)

    def test_load_web_archive_snapshot_should_not_save_stale_bookmark_data(self):
        bookmark = self.setup_bookmark()
        mock_cdx_api = create_cdx_server_api_mock()

        # update bookmark during API call to check that saving
        # the snapshot does not overwrite updated bookmark data
        def mock_newest_impl():
            bookmark.title = "Updated title"
            bookmark.save()
            return mock.DEFAULT

        mock_cdx_api.newest.side_effect = mock_newest_impl

        with mock.patch.object(
            bookmarks.services.wayback,
            "CustomWaybackMachineCDXServerAPI",
            return_value=mock_cdx_api,
        ):
            tasks._load_web_archive_snapshot_task(bookmark.id)
            self.run_pending_task(tasks._load_web_archive_snapshot_task)
            bookmark.refresh_from_db()

            self.assertEqual("Updated title", bookmark.title)
            self.assertEqual(
                "https://example.com/newest_snapshot", bookmark.web_archive_snapshot_url
            )

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_create_web_archive_snapshot_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        bookmark = self.setup_bookmark()
        tasks.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, False
        )

        self.assertEqual(Task.objects.count(), 0)

    def test_create_web_archive_snapshot_should_not_run_when_web_archive_integration_is_disabled(
        self,
    ):
        self.user.profile.web_archive_integration = (
            UserProfile.WEB_ARCHIVE_INTEGRATION_DISABLED
        )
        self.user.profile.save()

        bookmark = self.setup_bookmark()
        tasks.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, False
        )

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_bookmarks_without_snapshots_should_load_snapshot_for_all_bookmarks_without_snapshot(
        self,
    ):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(web_archive_snapshot_url="https://example.com")
        self.setup_bookmark(web_archive_snapshot_url="https://example.com")
        self.setup_bookmark(web_archive_snapshot_url="https://example.com")

        tasks.schedule_bookmarks_without_snapshots(user)
        self.run_pending_task(tasks._schedule_bookmarks_without_snapshots_task)

        task_list = Task.objects.all()
        self.assertEqual(task_list.count(), 3)

        for task in task_list:
            self.assertEqual(
                task.task_name,
                "bookmarks.services.tasks._load_web_archive_snapshot_task",
            )

    def test_schedule_bookmarks_without_snapshots_should_only_update_user_owned_bookmarks(
        self,
    ):
        user = self.get_or_create_test_user()
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
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
    def test_schedule_bookmarks_without_snapshots_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        tasks.schedule_bookmarks_without_snapshots(self.user)

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_bookmarks_without_snapshots_should_not_run_when_web_archive_integration_is_disabled(
        self,
    ):
        self.user.profile.web_archive_integration = (
            UserProfile.WEB_ARCHIVE_INTEGRATION_DISABLED
        )
        self.user.profile.save()
        tasks.schedule_bookmarks_without_snapshots(self.user)

        self.assertEqual(Task.objects.count(), 0)

    def test_load_favicon_should_create_favicon_file(self):
        bookmark = self.setup_bookmark()

        with mock.patch(
            "bookmarks.services.favicon_loader.load_favicon"
        ) as mock_load_favicon:
            mock_load_favicon.return_value = "https_example_com.png"

            tasks.load_favicon(self.get_or_create_test_user(), bookmark)
            self.run_pending_task(tasks._load_favicon_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.favicon_file, "https_example_com.png")

    def test_load_favicon_should_update_favicon_file(self):
        bookmark = self.setup_bookmark(favicon_file="https_example_com.png")

        with mock.patch(
            "bookmarks.services.favicon_loader.load_favicon"
        ) as mock_load_favicon:
            mock_load_favicon.return_value = "https_example_updated_com.png"
            tasks.load_favicon(self.get_or_create_test_user(), bookmark)
            self.run_pending_task(tasks._load_favicon_task)

            mock_load_favicon.assert_called()
            bookmark.refresh_from_db()
            self.assertEqual(bookmark.favicon_file, "https_example_updated_com.png")

    def test_load_favicon_should_handle_missing_bookmark(self):
        with mock.patch(
            "bookmarks.services.favicon_loader.load_favicon"
        ) as mock_load_favicon:
            tasks._load_favicon_task(123)
            self.run_pending_task(tasks._load_favicon_task)

            mock_load_favicon.assert_not_called()

    def test_load_favicon_should_not_save_stale_bookmark_data(self):
        bookmark = self.setup_bookmark()

        # update bookmark during API call to check that saving
        # the favicon does not overwrite updated bookmark data
        def mock_load_favicon_impl(url):
            bookmark.title = "Updated title"
            bookmark.save()
            return "https_example_com.png"

        with mock.patch(
            "bookmarks.services.favicon_loader.load_favicon"
        ) as mock_load_favicon:
            mock_load_favicon.side_effect = mock_load_favicon_impl

            tasks.load_favicon(self.get_or_create_test_user(), bookmark)
            self.run_pending_task(tasks._load_favicon_task)
            bookmark.refresh_from_db()

            self.assertEqual(bookmark.title, "Updated title")
            self.assertEqual(bookmark.favicon_file, "https_example_com.png")

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_load_favicon_should_not_run_when_background_tasks_are_disabled(self):
        bookmark = self.setup_bookmark()
        tasks.load_favicon(self.get_or_create_test_user(), bookmark)

        self.assertEqual(Task.objects.count(), 0)

    def test_load_favicon_should_not_run_when_favicon_feature_is_disabled(self):
        self.user.profile.enable_favicons = False
        self.user.profile.save()

        bookmark = self.setup_bookmark()
        tasks.load_favicon(self.get_or_create_test_user(), bookmark)

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_bookmarks_without_favicons_should_load_favicon_for_all_bookmarks_without_favicon(
        self,
    ):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(favicon_file="https_example_com.png")
        self.setup_bookmark(favicon_file="https_example_com.png")
        self.setup_bookmark(favicon_file="https_example_com.png")

        tasks.schedule_bookmarks_without_favicons(user)
        self.run_pending_task(tasks._schedule_bookmarks_without_favicons_task)

        task_list = Task.objects.all()
        self.assertEqual(task_list.count(), 3)

        for task in task_list:
            self.assertEqual(
                task.task_name, "bookmarks.services.tasks._load_favicon_task"
            )

    def test_schedule_bookmarks_without_favicons_should_only_update_user_owned_bookmarks(
        self,
    ):
        user = self.get_or_create_test_user()
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
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

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_schedule_bookmarks_without_favicons_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        bookmark = self.setup_bookmark()
        tasks.schedule_bookmarks_without_favicons(self.get_or_create_test_user())

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_bookmarks_without_favicons_should_not_run_when_favicon_feature_is_disabled(
        self,
    ):
        self.user.profile.enable_favicons = False
        self.user.profile.save()

        bookmark = self.setup_bookmark()
        tasks.schedule_bookmarks_without_favicons(self.get_or_create_test_user())

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_refresh_favicons_should_update_favicon_for_all_bookmarks(self):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(favicon_file="https_example_com.png")
        self.setup_bookmark(favicon_file="https_example_com.png")
        self.setup_bookmark(favicon_file="https_example_com.png")

        tasks.schedule_refresh_favicons(user)
        self.run_pending_task(tasks._schedule_refresh_favicons_task)

        task_list = Task.objects.all()
        self.assertEqual(task_list.count(), 6)

        for task in task_list:
            self.assertEqual(
                task.task_name, "bookmarks.services.tasks._load_favicon_task"
            )

    def test_schedule_refresh_favicons_should_only_update_user_owned_bookmarks(self):
        user = self.get_or_create_test_user()
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)

        tasks.schedule_refresh_favicons(user)
        self.run_pending_task(tasks._schedule_refresh_favicons_task)

        task_list = Task.objects.all()
        self.assertEqual(task_list.count(), 3)

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_schedule_refresh_favicons_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        self.setup_bookmark()
        tasks.schedule_refresh_favicons(self.get_or_create_test_user())

        self.assertEqual(Task.objects.count(), 0)

    @override_settings(LD_ENABLE_REFRESH_FAVICONS=False)
    def test_schedule_refresh_favicons_should_not_run_when_refresh_is_disabled(self):
        self.setup_bookmark()
        tasks.schedule_refresh_favicons(self.get_or_create_test_user())

        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_refresh_favicons_should_not_run_when_favicon_feature_is_disabled(
        self,
    ):
        self.user.profile.enable_favicons = False
        self.user.profile.save()

        self.setup_bookmark()
        tasks.schedule_refresh_favicons(self.get_or_create_test_user())

        self.assertEqual(Task.objects.count(), 0)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot_should_create_pending_asset(self):
        bookmark = self.setup_bookmark()

        with mock.patch("bookmarks.services.monolith.create_snapshot"):
            tasks.create_html_snapshot(bookmark)
            self.assertEqual(BookmarkAsset.objects.count(), 1)

            tasks.create_html_snapshot(bookmark)
            self.assertEqual(BookmarkAsset.objects.count(), 2)

            assets = BookmarkAsset.objects.filter(bookmark=bookmark)
            for asset in assets:
                self.assertEqual(asset.bookmark, bookmark)
                self.assertEqual(asset.asset_type, BookmarkAsset.TYPE_SNAPSHOT)
                self.assertEqual(asset.content_type, BookmarkAsset.CONTENT_TYPE_HTML)
                self.assertIn("HTML snapshot", asset.display_name)
                self.assertEqual(asset.status, BookmarkAsset.STATUS_PENDING)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot_should_update_file_info(self):
        bookmark = self.setup_bookmark(url="https://example.com")

        with mock.patch("bookmarks.services.singlefile.create_snapshot") as mock_create:
            tasks.create_html_snapshot(bookmark)
            asset = BookmarkAsset.objects.get(bookmark=bookmark)
            asset.date_created = datetime.datetime(2021, 1, 2, 3, 44, 55)
            asset.save()
            expected_filename = "snapshot_2021-01-02_034455_https___example.com.html.gz"

            self.run_pending_task(tasks._create_html_snapshot_task)

            mock_create.assert_called_once_with(
                "https://example.com",
                os.path.join(settings.LD_ASSET_FOLDER, expected_filename),
            )

            asset = BookmarkAsset.objects.get(bookmark=bookmark)
            self.assertEqual(asset.status, BookmarkAsset.STATUS_COMPLETE)
            self.assertEqual(asset.file, expected_filename)
            self.assertTrue(asset.gzip)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot_should_handle_error(self):
        bookmark = self.setup_bookmark(url="https://example.com")

        with mock.patch("bookmarks.services.singlefile.create_snapshot") as mock_create:
            mock_create.side_effect = singlefile.SingeFileError("Error")

            tasks.create_html_snapshot(bookmark)
            self.run_pending_task(tasks._create_html_snapshot_task)

            asset = BookmarkAsset.objects.get(bookmark=bookmark)
            self.assertEqual(asset.status, BookmarkAsset.STATUS_FAILURE)
            self.assertEqual(asset.file, "")
            self.assertFalse(asset.gzip)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot_should_handle_missing_bookmark(self):
        with mock.patch("bookmarks.services.singlefile.create_snapshot") as mock_create:
            tasks._create_html_snapshot_task(123)
            self.run_pending_task(tasks._create_html_snapshot_task)

            mock_create.assert_not_called()

    @override_settings(LD_ENABLE_SNAPSHOTS=False)
    def test_create_html_snapshot_should_not_run_when_single_file_is_disabled(
        self,
    ):
        bookmark = self.setup_bookmark()
        tasks.create_html_snapshot(bookmark)

        self.assertEqual(Task.objects.count(), 0)

    @override_settings(LD_ENABLE_SNAPSHOTS=True, LD_DISABLE_BACKGROUND_TASKS=True)
    def test_create_html_snapshot_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        bookmark = self.setup_bookmark()
        tasks.create_html_snapshot(bookmark)

        self.assertEqual(Task.objects.count(), 0)
