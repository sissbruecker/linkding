import datetime
import gzip
import os
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from bookmarks.models import BookmarkAsset
from bookmarks.services import assets
from bookmarks.tests.helpers import BookmarkFactoryMixin, disable_logging


class AssetServiceTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        self.setup_temp_assets_dir()
        self.get_or_create_test_user()

        self.html_content = "<html><body><h1>Hello, World!</h1></body></html>"
        self.mock_singlefile_create_snapshot_patcher = mock.patch(
            "bookmarks.services.singlefile.create_snapshot",
        )
        self.mock_singlefile_create_snapshot = (
            self.mock_singlefile_create_snapshot_patcher.start()
        )
        self.mock_singlefile_create_snapshot.side_effect = lambda url, filepath: (
            open(filepath, "w").write(self.html_content)
        )

    def tearDown(self) -> None:
        self.mock_singlefile_create_snapshot_patcher.stop()

    def get_saved_snapshot_file(self):
        # look up first file in the asset folder
        files = os.listdir(self.assets_dir)
        if files:
            return files[0]

    def test_create_snapshot_asset(self):
        bookmark = self.setup_bookmark()

        asset = assets.create_snapshot_asset(bookmark)

        self.assertIsNotNone(asset)
        self.assertEqual(asset.bookmark, bookmark)
        self.assertEqual(asset.asset_type, BookmarkAsset.TYPE_SNAPSHOT)
        self.assertEqual(asset.content_type, BookmarkAsset.CONTENT_TYPE_HTML)
        self.assertIn("HTML snapshot from", asset.display_name)
        self.assertEqual(asset.status, BookmarkAsset.STATUS_PENDING)

        # asset is not saved to the database
        self.assertIsNone(asset.id)

    def test_create_snapshot(self):
        initial_modified = timezone.datetime(
            2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        bookmark = self.setup_bookmark(
            url="https://example.com", modified=initial_modified
        )
        asset = assets.create_snapshot_asset(bookmark)
        asset.save()
        asset.date_created = timezone.datetime(
            2023, 8, 11, 21, 45, 11, tzinfo=datetime.timezone.utc
        )

        assets.create_snapshot(asset)

        expected_temp_filename = "snapshot_2023-08-11_214511_https___example.com.tmp"
        expected_temp_filepath = os.path.join(self.assets_dir, expected_temp_filename)
        expected_filename = "snapshot_2023-08-11_214511_https___example.com.html.gz"
        expected_filepath = os.path.join(self.assets_dir, expected_filename)

        # should call singlefile.create_snapshot with the correct arguments
        self.mock_singlefile_create_snapshot.assert_called_once_with(
            "https://example.com",
            expected_temp_filepath,
        )

        # should create gzip file in asset folder
        self.assertTrue(os.path.exists(expected_filepath))

        # gzip file should contain the correct content
        with gzip.open(expected_filepath, "rb") as gz_file:
            self.assertEqual(gz_file.read().decode(), self.html_content)

        # should remove temporary file
        self.assertFalse(os.path.exists(expected_temp_filepath))

        # should update asset status and file
        asset.refresh_from_db()
        self.assertEqual(asset.status, BookmarkAsset.STATUS_COMPLETE)
        self.assertEqual(asset.file, expected_filename)
        self.assertTrue(asset.gzip)

        # should update bookmark modified date
        bookmark.refresh_from_db()

    def test_create_snapshot_failure(self):
        bookmark = self.setup_bookmark(url="https://example.com")
        asset = assets.create_snapshot_asset(bookmark)
        asset.save()

        self.mock_singlefile_create_snapshot.side_effect = Exception

        with self.assertRaises(Exception):
            assets.create_snapshot(asset)

        asset.refresh_from_db()
        self.assertEqual(asset.status, BookmarkAsset.STATUS_FAILURE)

    def test_create_snapshot_truncates_asset_file_name(self):
        # Create a bookmark with a very long URL
        long_url = "http://" + "a" * 300 + ".com"
        bookmark = self.setup_bookmark(url=long_url)

        asset = assets.create_snapshot_asset(bookmark)
        asset.save()
        assets.create_snapshot(asset)

        saved_file = self.get_saved_snapshot_file()

        self.assertEqual(192, len(saved_file))
        self.assertTrue(saved_file.startswith("snapshot_"))
        self.assertTrue(saved_file.endswith("aaaa.html.gz"))

    def test_upload_snapshot(self):
        initial_modified = timezone.datetime(
            2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        bookmark = self.setup_bookmark(
            url="https://example.com", modified=initial_modified
        )
        asset = assets.upload_snapshot(bookmark, self.html_content.encode())

        # should create gzip file in asset folder
        saved_file_name = self.get_saved_snapshot_file()
        self.assertIsNotNone(saved_file_name)

        # verify file name
        self.assertTrue(saved_file_name.startswith("snapshot_"))
        self.assertTrue(saved_file_name.endswith("_https___example.com.html.gz"))

        # gzip file should contain the correct content
        with gzip.open(os.path.join(self.assets_dir, saved_file_name), "rb") as gz_file:
            self.assertEqual(gz_file.read().decode(), self.html_content)

        # should create asset
        self.assertIsNotNone(asset.id)
        self.assertEqual(asset.bookmark, bookmark)
        self.assertEqual(asset.asset_type, BookmarkAsset.TYPE_SNAPSHOT)
        self.assertEqual(asset.content_type, BookmarkAsset.CONTENT_TYPE_HTML)
        self.assertIn("HTML snapshot from", asset.display_name)
        self.assertEqual(asset.status, BookmarkAsset.STATUS_COMPLETE)
        self.assertEqual(asset.file, saved_file_name)
        self.assertTrue(asset.gzip)

        # should update bookmark modified date
        bookmark.refresh_from_db()
        self.assertGreater(bookmark.date_modified, initial_modified)

    def test_upload_snapshot_failure(self):
        bookmark = self.setup_bookmark(url="https://example.com")

        # make gzip.open raise an exception
        with mock.patch("gzip.open") as mock_gzip_open:
            mock_gzip_open.side_effect = Exception

            with self.assertRaises(Exception):
                assets.upload_snapshot(bookmark, b"invalid content")

        # asset is not saved to the database
        self.assertIsNone(BookmarkAsset.objects.first())

    def test_upload_snapshot_truncates_asset_file_name(self):
        # Create a bookmark with a very long URL
        long_url = "http://" + "a" * 300 + ".com"
        bookmark = self.setup_bookmark(url=long_url)

        assets.upload_snapshot(bookmark, self.html_content.encode())

        saved_file = self.get_saved_snapshot_file()

        self.assertEqual(192, len(saved_file))
        self.assertTrue(saved_file.startswith("snapshot_"))
        self.assertTrue(saved_file.endswith("aaaa.html.gz"))

    @disable_logging
    def test_upload_asset(self):
        initial_modified = timezone.datetime(
            2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        bookmark = self.setup_bookmark(modified=initial_modified)
        file_content = b"test content"
        upload_file = SimpleUploadedFile(
            "test_file.txt", file_content, content_type="text/plain"
        )

        asset = assets.upload_asset(bookmark, upload_file)

        # should create file in asset folder
        saved_file_name = self.get_saved_snapshot_file()
        self.assertIsNotNone(upload_file)

        # verify file name
        self.assertTrue(saved_file_name.startswith("upload_"))
        self.assertTrue(saved_file_name.endswith("_test_file.txt"))

        # file should contain the correct content
        with open(os.path.join(self.assets_dir, saved_file_name), "rb") as file:
            self.assertEqual(file.read(), file_content)

        # should create asset
        self.assertIsNotNone(asset.id)
        self.assertEqual(asset.bookmark, bookmark)
        self.assertEqual(asset.asset_type, BookmarkAsset.TYPE_UPLOAD)
        self.assertEqual(asset.content_type, upload_file.content_type)
        self.assertEqual(asset.display_name, upload_file.name)
        self.assertEqual(asset.status, BookmarkAsset.STATUS_COMPLETE)
        self.assertEqual(asset.file, saved_file_name)
        self.assertEqual(asset.file_size, len(file_content))
        self.assertFalse(asset.gzip)

        # should update bookmark modified date
        bookmark.refresh_from_db()
        self.assertGreater(bookmark.date_modified, initial_modified)

    @disable_logging
    def test_upload_asset_truncates_asset_file_name(self):
        # Create a bookmark with a very long URL
        long_file_name = "a" * 300 + ".txt"
        bookmark = self.setup_bookmark()

        file_content = b"test content"
        upload_file = SimpleUploadedFile(
            long_file_name, file_content, content_type="text/plain"
        )

        assets.upload_asset(bookmark, upload_file)

        saved_file = self.get_saved_snapshot_file()

        self.assertEqual(192, len(saved_file))
        self.assertTrue(saved_file.startswith("upload_"))
        self.assertTrue(saved_file.endswith("aaaa.txt"))

    @disable_logging
    def test_upload_asset_failure(self):
        bookmark = self.setup_bookmark()
        upload_file = SimpleUploadedFile("test_file.txt", b"test content")

        # make open raise an exception
        with mock.patch("builtins.open") as mock_open:
            mock_open.side_effect = Exception

            with self.assertRaises(Exception):
                assets.upload_asset(bookmark, upload_file)

        # asset is not saved to the database
        self.assertIsNone(BookmarkAsset.objects.first())

    def test_create_snapshot_updates_bookmark_latest_snapshot(self):
        bookmark = self.setup_bookmark(url="https://example.com")
        first_asset = assets.create_snapshot_asset(bookmark)
        first_asset.save()

        assets.create_snapshot(first_asset)
        bookmark.refresh_from_db()

        self.assertEqual(bookmark.latest_snapshot, first_asset)

        second_asset = assets.create_snapshot_asset(bookmark)
        second_asset.save()

        assets.create_snapshot(second_asset)
        bookmark.refresh_from_db()

        self.assertEqual(bookmark.latest_snapshot, second_asset)

    def test_upload_snapshot_updates_bookmark_latest_snapshot(self):
        bookmark = self.setup_bookmark(url="https://example.com")

        first_asset = assets.upload_snapshot(bookmark, self.html_content.encode())

        bookmark.refresh_from_db()
        self.assertEqual(bookmark.latest_snapshot, first_asset)

        second_asset = assets.upload_snapshot(bookmark, self.html_content.encode())

        bookmark.refresh_from_db()
        self.assertEqual(bookmark.latest_snapshot, second_asset)
        self.assertNotEqual(bookmark.latest_snapshot, first_asset)

    def test_create_snapshot_failure_does_not_update_latest_snapshot(self):
        # Create a bookmark with an existing latest_snapshot
        bookmark = self.setup_bookmark(url="https://example.com")
        initial_snapshot = assets.upload_snapshot(bookmark, self.html_content.encode())
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.latest_snapshot, initial_snapshot)

        # Create a new snapshot asset that will fail
        failing_asset = assets.create_snapshot_asset(bookmark)
        failing_asset.save()

        # Make the snapshot creation fail
        self.mock_singlefile_create_snapshot.side_effect = Exception(
            "Snapshot creation failed"
        )

        # Attempt to create a snapshot (which will fail)
        with self.assertRaises(Exception):
            assets.create_snapshot(failing_asset)

        # Verify that the bookmark's latest_snapshot is still the initial snapshot
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.latest_snapshot, initial_snapshot)

    def test_upload_snapshot_failure_does_not_update_latest_snapshot(self):
        # Create a bookmark with an existing latest_snapshot
        bookmark = self.setup_bookmark(url="https://example.com")
        initial_snapshot = assets.upload_snapshot(bookmark, self.html_content.encode())
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.latest_snapshot, initial_snapshot)

        # Make the gzip.open function fail
        with mock.patch("gzip.open") as mock_gzip_open:
            mock_gzip_open.side_effect = Exception("Upload failed")

            # Attempt to upload a snapshot (which will fail)
            with self.assertRaises(Exception):
                assets.upload_snapshot(bookmark, b"New content")

        # Verify that the bookmark's latest_snapshot is still the initial snapshot
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.latest_snapshot, initial_snapshot)

    def test_remove_latest_snapshot_updates_bookmark(self):
        # Create a bookmark with multiple snapshots
        bookmark = self.setup_bookmark()

        # Create base time (1 hour ago)
        base_time = timezone.now() - timedelta(hours=1)

        # Create three snapshots with explicitly different dates
        old_asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_COMPLETE,
            file="old_snapshot.html.gz",
            date_created=base_time,
        )
        self.setup_asset_file(old_asset)

        middle_asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_COMPLETE,
            file="middle_snapshot.html.gz",
            date_created=base_time + timedelta(minutes=30),
        )
        self.setup_asset_file(middle_asset)

        latest_asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_COMPLETE,
            file="latest_snapshot.html.gz",
            date_created=base_time + timedelta(minutes=60),
        )
        self.setup_asset_file(latest_asset)

        # Set the latest asset as the bookmark's latest_snapshot
        bookmark.latest_snapshot = latest_asset
        bookmark.save()

        # Delete the latest snapshot
        assets.remove_asset(latest_asset)
        bookmark.refresh_from_db()

        # Verify that middle_asset is now the latest_snapshot
        self.assertEqual(bookmark.latest_snapshot, middle_asset)

        # Delete the middle snapshot
        assets.remove_asset(middle_asset)
        bookmark.refresh_from_db()

        # Verify that old_asset is now the latest_snapshot
        self.assertEqual(bookmark.latest_snapshot, old_asset)

        # Delete the last snapshot
        assets.remove_asset(old_asset)
        bookmark.refresh_from_db()

        # Verify that latest_snapshot is now None
        self.assertIsNone(bookmark.latest_snapshot)

    def test_remove_non_latest_snapshot_does_not_affect_bookmark(self):
        # Create a bookmark with multiple snapshots
        bookmark = self.setup_bookmark()

        # Create base time (1 hour ago)
        base_time = timezone.now() - timedelta(hours=1)

        # Create two snapshots with explicitly different dates
        old_asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_COMPLETE,
            file="old_snapshot.html.gz",
            date_created=base_time,
        )
        self.setup_asset_file(old_asset)

        latest_asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_COMPLETE,
            file="latest_snapshot.html.gz",
            date_created=base_time + timedelta(minutes=30),
        )
        self.setup_asset_file(latest_asset)

        # Set the latest asset as the bookmark's latest_snapshot
        bookmark.latest_snapshot = latest_asset
        bookmark.save()

        # Delete the old snapshot (not the latest)
        assets.remove_asset(old_asset)
        bookmark.refresh_from_db()

        # Verify that latest_snapshot hasn't changed
        self.assertEqual(bookmark.latest_snapshot, latest_asset)

    @disable_logging
    def test_remove_asset(self):
        initial_modified = timezone.datetime(
            2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        bookmark = self.setup_bookmark(modified=initial_modified)
        file_content = b"test content for removal"
        upload_file = SimpleUploadedFile(
            "test_remove_file.txt", file_content, content_type="text/plain"
        )

        asset = assets.upload_asset(bookmark, upload_file)
        asset_filepath = os.path.join(self.assets_dir, asset.file)

        # Verify asset and file exist
        self.assertTrue(BookmarkAsset.objects.filter(id=asset.id).exists())
        self.assertTrue(os.path.exists(asset_filepath))

        bookmark.date_modified = initial_modified
        bookmark.save()

        # Remove the asset
        assets.remove_asset(asset)

        # Verify asset is removed from DB
        self.assertFalse(BookmarkAsset.objects.filter(id=asset.id).exists())
        # Verify file is removed from disk
        self.assertFalse(os.path.exists(asset_filepath))

        # Verify bookmark modified date is updated
        bookmark.refresh_from_db()
        self.assertGreater(bookmark.date_modified, initial_modified)
