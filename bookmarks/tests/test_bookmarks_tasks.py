import os.path
from unittest import mock

import waybackpy
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from huey.contrib.djhuey import HUEY as huey
from waybackpy.exceptions import WaybackError

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

        self.mock_load_preview_image_patcher = mock.patch(
            "bookmarks.services.preview_image_loader.load_preview_image"
        )
        self.mock_load_preview_image = self.mock_load_preview_image_patcher.start()
        self.mock_load_preview_image.return_value = "preview_image.png"

        user = self.get_or_create_test_user()
        user.profile.web_archive_integration = (
            UserProfile.WEB_ARCHIVE_INTEGRATION_ENABLED
        )
        user.profile.enable_favicons = True
        user.profile.enable_preview_images = True
        user.profile.save()

    def tearDown(self):
        self.mock_save_api_patcher.stop()
        self.mock_load_favicon_patcher.stop()
        self.mock_singlefile_create_snapshot_patcher.stop()
        self.mock_load_preview_image_patcher.stop()
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

    def test_load_preview_image_should_create_preview_image_file(self):
        bookmark = self.setup_bookmark()

        tasks.load_preview_image(self.get_or_create_test_user(), bookmark)
        bookmark.refresh_from_db()

        self.assertEqual(self.executed_count(), 1)
        self.assertEqual(bookmark.preview_image_file, "preview_image.png")

    def test_load_preview_image_should_update_preview_image_file(self):
        bookmark = self.setup_bookmark(
            preview_image_file="preview_image.png",
        )

        self.mock_load_preview_image.return_value = "preview_image_upd.png"

        tasks.load_preview_image(self.get_or_create_test_user(), bookmark)

        bookmark.refresh_from_db()
        self.mock_load_preview_image.assert_called_once()
        self.assertEqual(bookmark.preview_image_file, "preview_image_upd.png")

    def test_load_preview_image_should_set_blank_when_none_is_returned(self):
        bookmark = self.setup_bookmark(
            preview_image_file="preview_image.png",
        )

        self.mock_load_preview_image.return_value = None

        tasks.load_preview_image(self.get_or_create_test_user(), bookmark)

        bookmark.refresh_from_db()
        self.mock_load_preview_image.assert_called_once()
        self.assertEqual(bookmark.preview_image_file, "")

    def test_load_preview_image_should_handle_missing_bookmark(self):
        tasks._load_preview_image_task(123)

        self.mock_load_preview_image.assert_not_called()

    def test_load_preview_image_should_not_save_stale_bookmark_data(self):
        bookmark = self.setup_bookmark()

        # update bookmark during API call to check that saving
        # the image does not overwrite updated bookmark data
        def mock_load_preview_image_impl(url):
            bookmark.title = "Updated title"
            bookmark.save()
            return "test.png"

        self.mock_load_preview_image.side_effect = mock_load_preview_image_impl

        tasks.load_preview_image(self.get_or_create_test_user(), bookmark)
        bookmark.refresh_from_db()

        self.assertEqual(bookmark.title, "Updated title")
        self.assertEqual(bookmark.preview_image_file, "test.png")

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_load_preview_image_should_not_run_when_background_tasks_are_disabled(self):
        bookmark = self.setup_bookmark()
        tasks.load_preview_image(self.get_or_create_test_user(), bookmark)

        self.assertEqual(self.executed_count(), 0)

    def test_load_preview_image_should_not_run_when_preview_image_feature_is_disabled(
        self,
    ):
        self.user.profile.enable_preview_images = False
        self.user.profile.save()

        bookmark = self.setup_bookmark()
        tasks.load_preview_image(self.get_or_create_test_user(), bookmark)

        self.assertEqual(self.executed_count(), 0)

    def test_schedule_bookmarks_without_previews_should_load_preview_for_all_bookmarks_without_preview(
        self,
    ):
        user = self.get_or_create_test_user()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark(preview_image_file="test.png")
        self.setup_bookmark(preview_image_file="test.png")
        self.setup_bookmark(preview_image_file="test.png")

        tasks.schedule_bookmarks_without_previews(user)

        self.assertEqual(self.executed_count(), 4)
        self.assertEqual(self.mock_load_preview_image.call_count, 3)

    def test_schedule_bookmarks_without_previews_should_only_update_user_owned_bookmarks(
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

        tasks.schedule_bookmarks_without_previews(user)

        self.assertEqual(self.mock_load_preview_image.call_count, 3)

    @override_settings(LD_DISABLE_BACKGROUND_TASKS=True)
    def test_schedule_bookmarks_without_previews_should_not_run_when_background_tasks_are_disabled(
        self,
    ):
        self.setup_bookmark()
        tasks.schedule_bookmarks_without_previews(self.get_or_create_test_user())

        self.assertEqual(self.executed_count(), 0)

    def test_schedule_bookmarks_without_previews_should_not_run_when_preview_feature_is_disabled(
        self,
    ):
        self.user.profile.enable_preview_images = False
        self.user.profile.save()

        self.setup_bookmark()
        tasks.schedule_bookmarks_without_previews(self.get_or_create_test_user())

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

        self.mock_singlefile_create_snapshot.side_effect = singlefile.SingleFileError(
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

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_missing_html_snapshots(self):
        bookmarks_with_snapshots = []
        bookmarks_without_snapshots = []

        # setup bookmarks with snapshots
        bookmark = self.setup_bookmark()
        self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_COMPLETE,
        )
        bookmarks_with_snapshots.append(bookmark)

        bookmark = self.setup_bookmark()
        self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_PENDING,
        )
        bookmarks_with_snapshots.append(bookmark)

        # setup bookmarks without snapshots
        bookmark = self.setup_bookmark()
        bookmarks_without_snapshots.append(bookmark)

        bookmark = self.setup_bookmark()
        self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_FAILURE,
        )
        bookmarks_without_snapshots.append(bookmark)

        bookmark = self.setup_bookmark()
        self.setup_asset(
            bookmark=bookmark,
            asset_type="some_other_type",
            status=BookmarkAsset.STATUS_PENDING,
        )
        bookmarks_without_snapshots.append(bookmark)

        bookmark = self.setup_bookmark()
        self.setup_asset(
            bookmark=bookmark,
            asset_type="some_other_type",
            status=BookmarkAsset.STATUS_COMPLETE,
        )
        bookmarks_without_snapshots.append(bookmark)

        initial_assets = list(BookmarkAsset.objects.all())
        initial_assets_count = len(initial_assets)
        initial_asset_ids = [asset.id for asset in initial_assets]
        count = tasks.create_missing_html_snapshots(self.get_or_create_test_user())

        self.assertEqual(count, 4)
        self.assertEqual(BookmarkAsset.objects.count(), initial_assets_count + count)

        for bookmark in bookmarks_without_snapshots:
            new_assets = BookmarkAsset.objects.filter(bookmark=bookmark).exclude(
                id__in=initial_asset_ids
            )
            self.assertEqual(new_assets.count(), 1)

        for bookmark in bookmarks_with_snapshots:
            new_assets = BookmarkAsset.objects.filter(bookmark=bookmark).exclude(
                id__in=initial_asset_ids
            )
            self.assertEqual(new_assets.count(), 0)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_missing_html_snapshots_respects_current_user(self):
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        other_user = self.setup_user()
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)

        count = tasks.create_missing_html_snapshots(self.get_or_create_test_user())

        self.assertEqual(count, 3)
        self.assertEqual(BookmarkAsset.objects.count(), count)
