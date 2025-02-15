import os
import shutil
import tempfile

from django.conf import settings
from django.test import TestCase, override_settings

from bookmarks.services import bookmarks
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkPreviewsTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.override = override_settings(LD_PREVIEW_FOLDER=self.temp_dir)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.temp_dir)

    def setup_preview_file(self, filename):
        filepath = os.path.join(settings.LD_PREVIEW_FOLDER, filename)
        with open(filepath, "w") as f:
            f.write("test")

    def setup_bookmark_with_preview(self):
        bookmark = self.setup_bookmark()
        bookmark.preview_image_file = f"preview_{bookmark.id}.jpg"
        bookmark.save()
        self.setup_preview_file(bookmark.preview_image_file)
        return bookmark

    def assertPreviewImageExists(self, bookmark):
        self.assertTrue(
            os.path.exists(
                os.path.join(settings.LD_PREVIEW_FOLDER, bookmark.preview_image_file)
            )
        )

    def assertPreviewImageDoesNotExist(self, bookmark):
        self.assertFalse(
            os.path.exists(
                os.path.join(settings.LD_PREVIEW_FOLDER, bookmark.preview_image_file)
            )
        )

    def test_delete_bookmark_deletes_preview_image(self):
        bookmark = self.setup_bookmark_with_preview()
        self.assertPreviewImageExists(bookmark)

        bookmark.delete()
        self.assertPreviewImageDoesNotExist(bookmark)

    def test_bulk_delete_bookmarks_deletes_preview_images(self):
        bookmark1 = self.setup_bookmark_with_preview()
        bookmark2 = self.setup_bookmark_with_preview()
        bookmark3 = self.setup_bookmark_with_preview()

        self.assertPreviewImageExists(bookmark1)
        self.assertPreviewImageExists(bookmark2)
        self.assertPreviewImageExists(bookmark3)

        bookmarks.delete_bookmarks(
            [bookmark1.id, bookmark2.id, bookmark3.id], self.get_or_create_test_user()
        )

        self.assertPreviewImageDoesNotExist(bookmark1)
        self.assertPreviewImageDoesNotExist(bookmark2)
        self.assertPreviewImageDoesNotExist(bookmark3)
