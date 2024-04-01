import os

from django.conf import settings
from django.test import TestCase

from bookmarks.tests.helpers import (
    BookmarkFactoryMixin,
)
from bookmarks.services import bookmarks


class BookmarkAssetsTestCase(TestCase, BookmarkFactoryMixin):
    def tearDown(self):
        temp_files = [
            f for f in os.listdir(settings.LD_ASSET_FOLDER) if f.startswith("temp")
        ]
        for temp_file in temp_files:
            os.remove(os.path.join(settings.LD_ASSET_FOLDER, temp_file))

    def setup_asset_file(self, filename):
        if not os.path.exists(settings.LD_ASSET_FOLDER):
            os.makedirs(settings.LD_ASSET_FOLDER)
        filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
        with open(filepath, "w") as f:
            f.write("test")

    def setup_asset_with_file(self, bookmark):
        filename = f"temp_{bookmark.id}.html.gzip"
        self.setup_asset_file(filename)
        asset = self.setup_asset(bookmark=bookmark, file=filename)
        return asset

    def test_delete_bookmark_deletes_asset_file(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_file(bookmark)
        self.assertTrue(
            os.path.exists(os.path.join(settings.LD_ASSET_FOLDER, asset.file))
        )

        bookmark.delete()
        self.assertFalse(
            os.path.exists(os.path.join(settings.LD_ASSET_FOLDER, asset.file))
        )

    def test_bulk_delete_bookmarks_deletes_asset_files(self):
        bookmark1 = self.setup_bookmark()
        asset1 = self.setup_asset_with_file(bookmark1)
        bookmark2 = self.setup_bookmark()
        asset2 = self.setup_asset_with_file(bookmark2)
        bookmark3 = self.setup_bookmark()
        asset3 = self.setup_asset_with_file(bookmark3)
        self.assertTrue(
            os.path.exists(os.path.join(settings.LD_ASSET_FOLDER, asset1.file))
        )
        self.assertTrue(
            os.path.exists(os.path.join(settings.LD_ASSET_FOLDER, asset2.file))
        )
        self.assertTrue(
            os.path.exists(os.path.join(settings.LD_ASSET_FOLDER, asset3.file))
        )

        bookmarks.delete_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertFalse(
            os.path.exists(os.path.join(settings.LD_ASSET_FOLDER, asset1.file))
        )
        self.assertFalse(
            os.path.exists(os.path.join(settings.LD_ASSET_FOLDER, asset2.file))
        )
        self.assertFalse(
            os.path.exists(os.path.join(settings.LD_ASSET_FOLDER, asset3.file))
        )

    def test_save_updates_file_size(self):
        # File does not exist initially
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(bookmark=bookmark, file="temp.html.gz")
        self.assertIsNone(asset.file_size)

        # Add file, save again
        self.setup_asset_file(asset.file)
        asset.save()
        self.assertEqual(asset.file_size, 4)

        # Create asset with initial file
        asset = self.setup_asset(bookmark=bookmark, file="temp.html.gz")
        self.assertEqual(asset.file_size, 4)
