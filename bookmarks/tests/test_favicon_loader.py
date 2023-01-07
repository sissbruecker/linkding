import io
import os.path
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase

from bookmarks.services import favicon_loader

mock_icon_data = b'mock_icon'


class FaviconLoaderTestCase(TestCase):
    def setUp(self) -> None:
        self.clear_favicon_folder()

    def create_mock_response(self, icon_data=mock_icon_data):
        mock_response = mock.Mock()
        mock_response.raw = io.BytesIO(icon_data)
        return mock_response

    def clear_favicon_folder(self):
        folder = Path(settings.LD_FAVICON_FOLDER)
        for file in folder.iterdir():
            file.unlink()

    def icon_exists(self, filename):
        return Path(os.path.join(settings.LD_FAVICON_FOLDER, filename)).exists()

    def get_icon_data(self, filename):
        return Path(os.path.join(settings.LD_FAVICON_FOLDER, filename)).read_bytes()

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

    def test_load_favicon_updates_icon(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response()
            favicon_loader.load_favicon('https://example.com')

            updated_mock_icon_data = b'updated_mock_icon'
            mock_get.return_value = self.create_mock_response(icon_data=updated_mock_icon_data)
            favicon_loader.load_favicon('https://example.com')

            self.assertEqual(updated_mock_icon_data, self.get_icon_data('https_example_com.png'))

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

    def test_check_favicon(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response()

            self.assertFalse(favicon_loader.check_favicon('https://example.com'))

            favicon_loader.load_favicon('https://example.com')

            self.assertTrue(favicon_loader.check_favicon('https://example.com'))
