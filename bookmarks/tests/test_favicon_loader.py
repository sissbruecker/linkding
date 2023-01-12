import io
import os.path
import time
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase

from bookmarks.services import favicon_loader

mock_icon_data = b'mock_icon'


class FaviconLoaderTestCase(TestCase):
    def setUp(self) -> None:
        self.ensure_favicon_folder()
        self.clear_favicon_folder()

    def create_mock_response(self, icon_data=mock_icon_data):
        mock_response = mock.Mock()
        mock_response.raw = io.BytesIO(icon_data)
        return mock_response

    def ensure_favicon_folder(self):
        Path(settings.LD_FAVICON_FOLDER).mkdir(parents=True, exist_ok=True)

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
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon('https://example.com')

            # should create icon file
            self.assertTrue(self.icon_exists('https_example_com.png'))

            # should store image data
            self.assertEqual(mock_icon_data, self.get_icon_data('https_example_com.png'))

    def test_load_favicon_creates_folder_if_not_exists(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response()

            folder = Path(settings.LD_FAVICON_FOLDER)
            folder.rmdir()

            self.assertFalse(folder.exists())

            favicon_loader.load_favicon('https://example.com')

            self.assertTrue(folder.exists())

    def test_load_favicon_creates_single_icon_for_same_base_url(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon('https://example.com')
            favicon_loader.load_favicon('https://example.com?foo=bar')
            favicon_loader.load_favicon('https://example.com/foo')

            self.assertEqual(1, self.count_icons())
            self.assertTrue(self.icon_exists('https_example_com.png'))

    def test_load_favicon_creates_multiple_icons_for_different_base_url(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon('https://example.com')
            favicon_loader.load_favicon('https://sub.example.com')
            favicon_loader.load_favicon('https://other-domain.com')

            self.assertEqual(3, self.count_icons())
            self.assertTrue(self.icon_exists('https_example_com.png'))
            self.assertTrue(self.icon_exists('https_sub_example_com.png'))
            self.assertTrue(self.icon_exists('https_other_domain_com.png'))

    def test_load_favicon_caches_icons(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response()

            favicon_loader.load_favicon('https://example.com')
            mock_get.assert_called()

            mock_get.reset_mock()
            favicon_loader.load_favicon('https://example.com')
            mock_get.assert_not_called()

    def test_load_favicon_updates_stale_icon(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon('https://example.com')

            icon_path = self.get_icon_path('https_example_com.png')

            updated_mock_icon_data = b'updated_mock_icon'
            mock_get.return_value = self.create_mock_response(icon_data=updated_mock_icon_data)
            mock_get.reset_mock()

            # change icon modification date so it is not stale yet
            nearly_one_day_ago = time.time() - 60 * 60 * 23
            os.utime(icon_path.absolute(), (nearly_one_day_ago, nearly_one_day_ago))

            favicon_loader.load_favicon('https://example.com')
            mock_get.assert_not_called()

            # change icon modification date so it is considered stale
            one_day_ago = time.time() - 60 * 60 * 24
            os.utime(icon_path.absolute(), (one_day_ago, one_day_ago))

            favicon_loader.load_favicon('https://example.com')
            mock_get.assert_called()
            self.assertEqual(updated_mock_icon_data, self.get_icon_data('https_example_com.png'))
