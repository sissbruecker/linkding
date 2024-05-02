import io
import os
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase

from bookmarks.services import preview_image_loader

mock_icon_data = b"mock_icon"


class MockStreamingResponse:
    def __init__(self, data=mock_icon_data, content_type="image/png"):
        self.chunks = [data]
        self.headers = {"Content-Type": content_type}

    def iter_content(self, **kwargs):
        return self.chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class PreviewImageLoaderTestCase(TestCase):
    def setUp(self) -> None:
        self.temp_folder = tempfile.TemporaryDirectory()
        self.settings_override = self.settings(LD_PREVIEW_FOLDER=self.temp_folder.name)
        self.settings_override.enable()

    def tearDown(self) -> None:
        self.temp_folder.cleanup()
        self.settings_override.disable()

    def create_mock_response(self, icon_data=mock_icon_data, content_type="image/png"):
        mock_response = mock.Mock()
        mock_response.raw = io.BytesIO(icon_data)
        return MockStreamingResponse(icon_data, content_type)

    def get_image_path(self, filename):
        return Path(os.path.join(settings.LD_PREVIEW_FOLDER, filename))

    def image_exists(self, filename):
        return self.get_image_path(filename).exists()

    def get_image_data(self, filename):
        return self.get_image_path(filename).read_bytes()

    def test_load_preview_image(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()

            file = preview_image_loader.load_preview_image(
                "https://example.com/image.png"
            )

            self.assertTrue(self.image_exists(file))
            self.assertEqual(mock_icon_data, self.get_image_data(file))

    def test_load_preview_image_creates_folder_if_not_exists(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()

            folder = Path(settings.LD_PREVIEW_FOLDER)
            folder.rmdir()

            self.assertFalse(folder.exists())

            preview_image_loader.load_preview_image("https://example.com/image.png")

            self.assertTrue(folder.exists())

    def test_guess_file_extension(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(content_type="image/png")
            file = preview_image_loader.load_preview_image("https://example.com/image1")

            self.assertTrue(self.image_exists(file))
            self.assertEqual("png", file.split(".")[-1])

        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(content_type="image/jpeg")
            file = preview_image_loader.load_preview_image("https://example.com/image2")

            self.assertTrue(self.image_exists(file))
            self.assertEqual("jpg", file.split(".")[-1])
