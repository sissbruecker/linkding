import io
import os.path
import time
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from bookmarks.services import favicon_loader

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


class FaviconLoaderTestCase(TestCase):
    def setUp(self) -> None:
        self.temp_favicon_folder = tempfile.TemporaryDirectory()
        self.favicon_folder_override = self.settings(
            LD_FAVICON_FOLDER=self.temp_favicon_folder.name
        )
        self.favicon_folder_override.enable()

    def tearDown(self) -> None:
        self.temp_favicon_folder.cleanup()
        self.favicon_folder_override.disable()

    def create_mock_response(self, icon_data=mock_icon_data, content_type="image/png"):
        mock_response = mock.Mock()
        mock_response.raw = io.BytesIO(icon_data)
        return MockStreamingResponse(icon_data, content_type)

    def clear_favicon_folder(self):
        folder = Path(settings.LD_FAVICON_FOLDER)
        for file in folder.iterdir():
            file.unlink()

    def get_icon_path(self, filename):
        return Path(os.path.join(settings.LD_FAVICON_FOLDER, filename))

    def icon_exists(self, filename):
        return self.get_icon_path(filename).exists()

    def get_icon_data(self, filename):
        return self.get_icon_path(filename).read_bytes()

    def count_icons(self):
        files = os.listdir(settings.LD_FAVICON_FOLDER)
        return len(files)

    def test_load_favicon(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon("https://example.com")

            # should create icon file
            self.assertTrue(self.icon_exists("https_example_com.png"))

            # should store image data
            self.assertEqual(
                mock_icon_data, self.get_icon_data("https_example_com.png")
            )

    def test_load_favicon_creates_folder_if_not_exists(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()

            folder = Path(settings.LD_FAVICON_FOLDER)
            folder.rmdir()

            self.assertFalse(folder.exists())

            favicon_loader.load_favicon("https://example.com")

            self.assertTrue(folder.exists())

    def test_load_favicon_creates_single_icon_for_same_base_url(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon("https://example.com")
            favicon_loader.load_favicon("https://example.com?foo=bar")
            favicon_loader.load_favicon("https://example.com/foo")

            self.assertEqual(1, self.count_icons())
            self.assertTrue(self.icon_exists("https_example_com.png"))

    def test_load_favicon_creates_multiple_icons_for_different_base_url(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon("https://example.com")
            favicon_loader.load_favicon("https://sub.example.com")
            favicon_loader.load_favicon("https://other-domain.com")

            self.assertEqual(3, self.count_icons())
            self.assertTrue(self.icon_exists("https_example_com.png"))
            self.assertTrue(self.icon_exists("https_sub_example_com.png"))
            self.assertTrue(self.icon_exists("https_other_domain_com.png"))

    def test_load_favicon_caches_icons(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()

            favicon_file = favicon_loader.load_favicon("https://example.com")
            mock_get.assert_called()
            self.assertEqual(favicon_file, "https_example_com.png")

            mock_get.reset_mock()
            updated_favicon_file = favicon_loader.load_favicon("https://example.com")
            mock_get.assert_not_called()
            self.assertEqual(favicon_file, updated_favicon_file)

    def test_load_favicon_updates_stale_icon(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon("https://example.com")

            icon_path = self.get_icon_path("https_example_com.png")

            updated_mock_icon_data = b"updated_mock_icon"
            mock_get.return_value = self.create_mock_response(
                icon_data=updated_mock_icon_data
            )
            mock_get.reset_mock()

            # change icon modification date so it is not stale yet
            nearly_one_day_ago = time.time() - 60 * 60 * 23
            os.utime(icon_path.absolute(), (nearly_one_day_ago, nearly_one_day_ago))

            favicon_loader.load_favicon("https://example.com")
            mock_get.assert_not_called()

            # change icon modification date so it is considered stale
            one_day_ago = time.time() - 60 * 60 * 24
            os.utime(icon_path.absolute(), (one_day_ago, one_day_ago))

            favicon_loader.load_favicon("https://example.com")
            mock_get.assert_called()
            self.assertEqual(
                updated_mock_icon_data, self.get_icon_data("https_example_com.png")
            )

    @override_settings(LD_FAVICON_PROVIDER="https://custom.icons.com/?url={url}")
    def test_custom_provider_with_url_param(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()

            favicon_loader.load_favicon("https://example.com/foo?bar=baz")
            mock_get.assert_called_with(
                "https://custom.icons.com/?url=https://example.com", stream=True
            )

    @override_settings(LD_FAVICON_PROVIDER="https://custom.icons.com/?url={domain}")
    def test_custom_provider_with_domain_param(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response()

            favicon_loader.load_favicon("https://example.com/foo?bar=baz")
            mock_get.assert_called_with(
                "https://custom.icons.com/?url=example.com", stream=True
            )

    def test_guess_file_extension(self):
        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(content_type="image/png")
            favicon_loader.load_favicon("https://example.com")

            self.assertTrue(self.icon_exists("https_example_com.png"))

        self.clear_favicon_folder()

        with mock.patch("requests.get") as mock_get:
            mock_get.return_value = self.create_mock_response(
                content_type="image/x-icon"
            )
            favicon_loader.load_favicon("https://example.com")

            self.assertTrue(self.icon_exists("https_example_com.ico"))
