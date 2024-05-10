import io
import os
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase

from bookmarks.services import preview_image_loader

mock_image_data = b"mock_image"


class MockStreamingResponse:
    def __init__(
        self,
        url,
        data=mock_image_data,
        content_type="image/png",
        content_length=None,
        status_code=200,
    ):
        self.url = url
        self.chunks = [data]
        self.status_code = status_code
        if not content_length:
            content_length = len(data)
        self.headers = {"Content-Type": content_type, "Content-Length": content_length}

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
        self.mock_load_website_metadata_patcher = mock.patch(
            "bookmarks.services.website_loader.load_website_metadata"
        )
        self.mock_load_website_metadata = (
            self.mock_load_website_metadata_patcher.start()
        )
        self.mock_load_website_metadata.return_value = mock.Mock(
            preview_image="https://example.com/image.png"
        )

    def tearDown(self) -> None:
        self.temp_folder.cleanup()
        self.settings_override.disable()
        self.mock_load_website_metadata_patcher.stop()

    def create_mock_response(
        self,
        url="https://example.com/image.png",
        icon_data=mock_image_data,
        content_type="image/png",
        content_length=len(mock_image_data),
        status_code=200,
    ):
        mock_response = mock.Mock()
        mock_response.raw = io.BytesIO(icon_data)
        return MockStreamingResponse(
            url, icon_data, content_type, content_length, status_code
        )

    def get_image_path(self, filename):
        return Path(os.path.join(settings.LD_PREVIEW_FOLDER, filename))

    def assertImageExists(self, filename, data):
        self.assertTrue(self.get_image_path(filename).exists())
        self.assertEqual(self.get_image_path(filename).read_bytes(), data)

    def assertNoImageExists(self):
        self.assertFalse(os.listdir(settings.LD_PREVIEW_FOLDER))

    def test_load_preview_image(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()

            file = preview_image_loader.load_preview_image("https://example.com")

            self.assertIsNotNone(file)
            self.assertImageExists(file, mock_image_data)

    def test_load_preview_image_returns_none_if_no_preview_image_detected(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()
            self.mock_load_website_metadata.return_value = mock.Mock(preview_image=None)

            file = preview_image_loader.load_preview_image("https://example.com")

            self.assertIsNone(file)
            self.assertNoImageExists()

    def test_load_preview_image_returns_none_for_invalid_status_code(self):
        invalid_status_codes = [199, 300, 400, 500]

        for status_code in invalid_status_codes:
            with mock.patch("requests.get") as mock_get:
                mock_get.return_value = self.create_mock_response(
                    status_code=status_code
                )

                file = preview_image_loader.load_preview_image("https://example.com")

                self.assertIsNone(file)
                self.assertNoImageExists()

    def test_load_preview_image_returns_none_if_content_length_exceeds_limit(self):
        # exceeds max size
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(
                content_length=settings.LD_PREVIEW_MAX_SIZE + 1
            )

            file = preview_image_loader.load_preview_image("https://example.com")

            self.assertIsNone(file)
            self.assertNoImageExists()

        # equals max size
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(
                content_length=settings.LD_PREVIEW_MAX_SIZE
            )

            file = preview_image_loader.load_preview_image("https://example.com")

            self.assertIsNotNone(file)
            self.assertImageExists(file, mock_image_data)

    def test_load_preview_image_returns_none_for_invalid_content_type(self):
        invalid_content_types = ["text/html", "application/json"]

        for content_type in invalid_content_types:
            with mock.patch("requests.get") as mock_get:
                mock_get.return_value = self.create_mock_response(
                    content_type=content_type
                )

                file = preview_image_loader.load_preview_image("https://example.com")

                self.assertIsNone(file)
                self.assertNoImageExists()

        valid_content_types = ["image/png", "image/jpeg", "image/gif"]

        for content_type in valid_content_types:
            with mock.patch("requests.get") as mock_get:
                mock_get.return_value = self.create_mock_response(
                    content_type=content_type
                )

                file = preview_image_loader.load_preview_image("https://example.com")

                self.assertIsNotNone(file)
                self.assertImageExists(file, mock_image_data)

    def test_load_preview_image_returns_none_if_download_exceeds_content_length(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(content_length=1)

            file = preview_image_loader.load_preview_image("https://example.com")

            self.assertIsNone(file)
            self.assertNoImageExists()

    def test_load_preview_image_creates_folder_if_not_exists(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()

            folder = Path(settings.LD_PREVIEW_FOLDER)
            folder.rmdir()

            self.assertFalse(folder.exists())

            preview_image_loader.load_preview_image("https://example.com")

            self.assertTrue(folder.exists())

    def test_guess_file_extension(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(content_type="image/png")

            file = preview_image_loader.load_preview_image("https://example.com")

            self.assertImageExists(file, mock_image_data)
            self.assertEqual("png", file.split(".")[-1])

        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(content_type="image/jpeg")

            file = preview_image_loader.load_preview_image("https://example.com")

            self.assertImageExists(file, mock_image_data)
            self.assertEqual("jpg", file.split(".")[-1])
