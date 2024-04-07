import datetime
import os.path
from dataclasses import dataclass
from unittest import mock

import waybackpy
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from huey.contrib.djhuey import HUEY as huey
from waybackpy.exceptions import WaybackError

import bookmarks.services.favicon_loader
import bookmarks.services.wayback
from bookmarks.models import BookmarkAsset, UserProfile
from bookmarks.services import tasks, singlefile
from bookmarks.tests.helpers import BookmarkFactoryMixin


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


class BookmarkTasksTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self):
        huey.immediate = True
        huey.results = True
        huey.store_none = True

        self.mock_save_api = mock.Mock(
            archive_url="https://example.com/created_snapshot"
        )
        self.mock_save_api_patcher = mock.patch.object(
            waybackpy, "WaybackMachineSaveAPI", return_value=self.mock_save_api
        )
        self.mock_save_api_patcher.start()

        self.mock_cdx_api = mock.Mock()
        self.mock_cdx_api.newest.return_value = MockCdxSnapshot(
            "https://example.com/newest_snapshot", datetime.datetime.now()
        )
        self.mock_cdx_api_patcher = mock.patch.object(
            bookmarks.services.wayback,
            "CustomWaybackMachineCDXServerAPI",
            return_value=self.mock_cdx_api,
        )
        self.mock_cdx_api_patcher.start()

        self.mock_load_favicon_patcher = mock.patch(
            "bookmarks.services.favicon_loader.load_favicon"
        )
        self.mock_load_favicon = self.mock_load_favicon_patcher.start()
        self.mock_load_favicon.return_value = "https_example_com.png"

        self.mock_singlefile_create_snapshot_patcher = mock.patch(
            "bookmarks.services.singlefile.create_snapshot",
        )
        self.mock_singlefile_create_snapshot = (
            self.mock_singlefile_create_snapshot_patcher.start()
        )

        user = self.get_or_create_test_user()
        user.profile.web_archive_integration = (
            UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED
        )
        user.profile.enable_favicons = True
        user.profile.save()

    def tearDown(self):
        self.mock_save_api_patcher.stop()
        self.mock_cdx_api_patcher.stop()
        self.mock_load_favicon_patcher.stop()
        self.mock_singlefile_create_snapshot_patcher.stop()
        huey.storage.flush_results()
        huey.immediate = False

    def executed_count(self):
        return len(huey.all_results())

    def test_create_web_archive_snapshot_should_update_snapshot_url(self):
        bookmark = self.setup_bookmark()

        tasks.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, False
        )
        bookmark.refresh_from_db()

        self.mock_save_api.save.assert_called_once()
        self.assertEqual(self.executed_count(), 1)
        self.assertEqual(
            bookmark.web_archive_snapshot_url,
            "https://example.com/created_snapshot",
        )

    def test_create_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        tasks._create_web_archive_snapshot_task(123, False)

        self.assertEqual(self.executed_count(), 1)
        self.mock_save_api.save.assert_not_called()

    def test_create_web_archive_snapshot_should_skip_if_snapshot_exists(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com")

        self.mock_save_api.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, False
        )

        self.assertEqual(self.executed_count(), 0)
        self.mock_save_api.assert_not_called()

    def test_create_web_archive_snapshot_should_force_update_snapshot(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com")
        self.mock_save_api.archive_url = "https://other.com"

        tasks.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, True
        )
        bookmark.refresh_from_db()

        self.assertEqual(bookmark.web_archive_snapshot_url, "https://other.com")

    def test_create_web_archive_snapshot_should_use_newest_snapshot_as_fallback(self):
        bookmark = self.setup_bookmark()
        self.mock_save_api.save.side_effect = WaybackError

        tasks.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, False
        )

        bookmark.refresh_from_db()
        self.mock_cdx_api.newest.assert_called_once()
        self.assertEqual(
            "https://example.com/newest_snapshot",
            bookmark.web_archive_snapshot_url,
        )

    def test_create_web_archive_snapshot_should_ignore_missing_newest_snapshot(self):
        bookmark = self.setup_bookmark()
        self.mock_save_api.save.side_effect = WaybackError
        self.mock_cdx_api.newest.return_value = None

        tasks.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, False
        )

        bookmark.refresh_from_db()
        self.assertEqual("", bookmark.web_archive_snapshot_url)

    def test_create_web_archive_snapshot_should_ignore_newest_snapshot_errors(self):
        bookmark = self.setup_bookmark()
        self.mock_save_api.save.side_effect = WaybackError
        self.mock_cdx_api.newest.side_effect = WaybackError

        tasks.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, False
        )

        bookmark.refresh_from_db()
        self.assertEqual("", bookmark.web_archive_snapshot_url)

    def test_create_web_archive_snapshot_should_not_save_stale_bookmark_data(self):
        bookmark = self.setup_bookmark()

        # update bookmark during API call to check that saving
        # the snapshot does not overwrite updated bookmark data
        def mock_save_impl():
            bookmark.title = "Updated title"
            bookmark.save()

        self.mock_save_api.save.side_effect = mock_save_impl

        tasks.create_web_archive_snapshot(
            self.get_or_create_test_user(), bookmark, False
        )
        bookmark.refresh_from_db()

        self.assertEqual(bookmark.title, "Updated title")
        self.assertEqual(
            "https://example.com/created_snapshot",
            bookmark.web_archive_snapshot_url,
        )

    def test_load_web_archive_snapshot_should_update_snapshot_url(self):
        bookmark = self.setup_bookmark()

        tasks._load_web_archive_snapshot_task(bookmark.id)

        bookmark.refresh_from_db()

        self.assertEqual(self.executed_count(), 1)
        self.mock_cdx_api.newest.assert_called_once()
        self.assertEqual(
            "https://example.com/newest_snapshot", bookmark.web_archive_snapshot_url
        )

    def test_load_web_archive_snapshot_should_handle_missing_bookmark_id(self):
        tasks._load_web_archive_snapshot_task(123)

        self.assertEqual(self.executed_count(), 1)
        self.mock_cdx_api.newest.assert_not_called()

    def test_load_web_archive_snapshot_should_skip_if_snapshot_exists(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com")

        tasks._load_web_archive_snapshot_task(bookmark.id)

        self.assertEqual(self.executed_count(), 1)
        self.mock_cdx_api.newest.assert_not_called()

    def test_load_web_archive_snapshot_should_handle_missing_snapshot(self):
        bookmark = self.setup_bookmark()
        self.mock_cdx_api.newest.return_value = None

        tasks._load_web_archive_snapshot_task(bookmark.id)

        self.assertEqual("", bookmark.web_archive_snapshot_url)

    def test_load_web_archive_snapshot_should_handle_wayback_errors(self):
        bookmark = self.setup_bookmark()
        self.mock_cdx_api.newest.side_effect = WaybackError

        tasks._load_web_archive_snapshot_task(bookmark.id)

        self.assertEqual("", bookmark.web_archive_snapshot_url)

    def test_load_web_archive_snapshot_should_not_save_stale_bookmark_data(self):
        bookmark = self.setup_bookmark()

        # update bookmark during API call to check that saving
        # the snapshot does not overwrite updated bookmark data
        def mock_newest_impl():
            bookmark.title = "Updated title"
            bookmark.save()
            return mock.DEFAULT

        self.mock_cdx_api.newest.side_effect = mock_newest_impl

        tasks._load_web_archive_snapshot_task(bookmark.id)
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
        self.assertEqual(self.executed_count(), 0)

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

        self.assertEqual(self.executed_count(), 0)

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

        self.assertEqual(self.executed_count(), 4)
        self.assertEqual(self.mock_cdx_api.newest.call_count, 3)

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

        self.assertEqual(self.mock_cdx_api.newest.call_count, 3)

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_schedule_bookmarks_without_snapshots_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        tasks.schedule_bookmarks_without_snapshots(self.user)

        self.assertEqual(self.executed_count(), 0)

    def test_schedule_bookmarks_without_snapshots_should_not_run_when_web_archive_integration_is_disabled(
        self,
    ):
        self.user.profile.web_archive_integration = (
            UserProfile.WEB_ARCHIVE_INTEGRATION_DISABLED
        )
        self.user.profile.save()
        tasks.schedule_bookmarks_without_snapshots(self.user)

        self.assertEqual(self.executed_count(), 0)

    def test_load_favicon_should_create_favicon_file(self):
        bookmark = self.setup_bookmark()

        tasks.load_favicon(self.get_or_create_test_user(), bookmark)
        bookmark.refresh_from_db()

        self.assertEqual(self.executed_count(), 1)
        self.assertEqual(bookmark.favicon_file, "https_example_com.png")

    def test_load_favicon_should_update_favicon_file(self):
        bookmark = self.setup_bookmark(favicon_file="https_example_com.png")

        self.mock_load_favicon.return_value = "https_example_updated_com.png"

        tasks.load_favicon(self.get_or_create_test_user(), bookmark)

        bookmark.refresh_from_db()
        self.mock_load_favicon.assert_called_once()
        self.assertEqual(bookmark.favicon_file, "https_example_updated_com.png")

    def test_load_favicon_should_handle_missing_bookmark(self):
        tasks._load_favicon_task(123)

        self.mock_load_favicon.assert_not_called()

    def test_load_favicon_should_not_save_stale_bookmark_data(self):
        bookmark = self.setup_bookmark()

        # update bookmark during API call to check that saving
        # the favicon does not overwrite updated bookmark data
        def mock_load_favicon_impl(url):
            bookmark.title = "Updated title"
            bookmark.save()
            return "https_example_com.png"

        self.mock_load_favicon.side_effect = mock_load_favicon_impl

        tasks.load_favicon(self.get_or_create_test_user(), bookmark)
        bookmark.refresh_from_db()

        self.assertEqual(bookmark.title, "Updated title")
        self.assertEqual(bookmark.favicon_file, "https_example_com.png")

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_load_favicon_should_not_run_when_background_tasks_are_disabled(self):
        bookmark = self.setup_bookmark()
        tasks.load_favicon(self.get_or_create_test_user(), bookmark)

        self.assertEqual(self.executed_count(), 0)

    def test_load_favicon_should_not_run_when_favicon_feature_is_disabled(self):
        self.user.profile.enable_favicons = False
        self.user.profile.save()

        bookmark = self.setup_bookmark()
        tasks.load_favicon(self.get_or_create_test_user(), bookmark)

        self.assertEqual(self.executed_count(), 0)

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

        self.assertEqual(self.executed_count(), 4)
        self.assertEqual(self.mock_load_favicon.call_count, 3)

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

        self.assertEqual(self.mock_load_favicon.call_count, 3)

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_schedule_bookmarks_without_favicons_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        self.setup_bookmark()
        tasks.schedule_bookmarks_without_favicons(self.get_or_create_test_user())

        self.assertEqual(self.executed_count(), 0)

    def test_schedule_bookmarks_without_favicons_should_not_run_when_favicon_feature_is_disabled(
        self,
    ):
        self.user.profile.enable_favicons = False
        self.user.profile.save()

        self.setup_bookmark()
        tasks.schedule_bookmarks_without_favicons(self.get_or_create_test_user())

        self.assertEqual(self.executed_count(), 0)

    def test_schedule_refresh_favicons_should_update_favicon_for_all_bookmarks(self):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(favicon_file="https_example_com.png")
        self.setup_bookmark(favicon_file="https_example_com.png")
        self.setup_bookmark(favicon_file="https_example_com.png")

        tasks.schedule_refresh_favicons(user)

        self.assertEqual(self.executed_count(), 7)
        self.assertEqual(self.mock_load_favicon.call_count, 6)

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

        self.assertEqual(self.mock_load_favicon.call_count, 3)

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_schedule_refresh_favicons_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        self.setup_bookmark()
        tasks.schedule_refresh_favicons(self.get_or_create_test_user())

        self.assertEqual(self.executed_count(), 0)

    @override_settings(LD_ENABLE_REFRESH_FAVICONS=False)
    def test_schedule_refresh_favicons_should_not_run_when_refresh_is_disabled(self):
        self.setup_bookmark()
        tasks.schedule_refresh_favicons(self.get_or_create_test_user())

        self.assertEqual(self.executed_count(), 0)

    def test_schedule_refresh_favicons_should_not_run_when_favicon_feature_is_disabled(
        self,
    ):
        self.user.profile.enable_favicons = False
        self.user.profile.save()

        self.setup_bookmark()
        tasks.schedule_refresh_favicons(self.get_or_create_test_user())

        self.assertEqual(self.executed_count(), 0)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot_should_create_pending_asset(self):
        bookmark = self.setup_bookmark()

        # Mock the task function to avoid running it immediately
        with mock.patch("bookmarks.services.tasks._create_html_snapshot_task"):
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

        with mock.patch(
            "bookmarks.services.tasks._generate_snapshot_filename"
        ) as mock_generate:
            expected_filename = "snapshot_2021-01-02_034455_https___example.com.html.gz"
            mock_generate.return_value = expected_filename

            tasks.create_html_snapshot(bookmark)
            BookmarkAsset.objects.get(bookmark=bookmark)

            # Run periodic task to process the snapshot
            tasks._schedule_html_snapshots_task()

            self.mock_singlefile_create_snapshot.assert_called_once_with(
                "https://example.com",
                os.path.join(
                    settings.LD_ASSET_FOLDER,
                    expected_filename,
                ),
            )

            asset = BookmarkAsset.objects.get(bookmark=bookmark)
            self.assertEqual(asset.status, BookmarkAsset.STATUS_COMPLETE)
            self.assertEqual(asset.file, expected_filename)
            self.assertTrue(asset.gzip)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot_truncate_filename(self):
        # Create a bookmark with a very long URL
        long_url = "http://" + "a" * 300 + ".com"
        bookmark = self.setup_bookmark(url=long_url)

        tasks.create_html_snapshot(bookmark)
        BookmarkAsset.objects.get(bookmark=bookmark)

        # Run periodic task to process the snapshot
        tasks._schedule_html_snapshots_task()

        asset = BookmarkAsset.objects.get(bookmark=bookmark)
        self.assertEqual(len(asset.file), 192)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot_should_handle_error(self):
        bookmark = self.setup_bookmark(url="https://example.com")

        self.mock_singlefile_create_snapshot.side_effect = singlefile.SingeFileError(
            "Error"
        )
        tasks.create_html_snapshot(bookmark)

        # Run periodic task to process the snapshot
        tasks._schedule_html_snapshots_task()

        asset = BookmarkAsset.objects.get(bookmark=bookmark)
        self.assertEqual(asset.status, BookmarkAsset.STATUS_FAILURE)
        self.assertEqual(asset.file, "")
        self.assertFalse(asset.gzip)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_html_snapshot_should_handle_missing_bookmark(self):
        tasks._create_html_snapshot_task(123)

        self.mock_singlefile_create_snapshot.assert_not_called()

    @override_settings(LD_ENABLE_SNAPSHOTS=False)
    def test_create_html_snapshot_should_not_create_asset_when_single_file_is_disabled(
        self,
    ):
        bookmark = self.setup_bookmark()
        tasks.create_html_snapshot(bookmark)

        self.assertEqual(BookmarkAsset.objects.count(), 0)

    @override_settings(LD_ENABLE_SNAPSHOTS=True, LD_DISABLE_BACKGROUND_TASKS=True)
    def test_create_html_snapshot_should_not_create_asset_when_background_tasks_are_disabled(
        self,
    ):
        bookmark = self.setup_bookmark()
        tasks.create_html_snapshot(bookmark)

        self.assertEqual(BookmarkAsset.objects.count(), 0)
