import gzip
import os
from unittest import mock
import subprocess

from django.test import TestCase

from bookmarks.services import monolith


class MonolithServiceTestCase(TestCase):
    html_content = "<html><body><h1>Hello, World!</h1></body></html>"
    html_filepath = "temp.html.gz"
    temp_html_filepath = "temp.html.gz.tmp"

    def tearDown(self):
        if os.path.exists(self.html_filepath):
            os.remove(self.html_filepath)
        if os.path.exists(self.temp_html_filepath):
            os.remove(self.temp_html_filepath)

    def create_test_file(self, *args, **kwargs):
        with open(self.temp_html_filepath, "w") as file:
            file.write(self.html_content)

    def test_create_snapshot(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = self.create_test_file

            monolith.create_snapshot("http://example.com", self.html_filepath)

            self.assertTrue(os.path.exists(self.html_filepath))
            self.assertFalse(os.path.exists(self.temp_html_filepath))

            with gzip.open(self.html_filepath, "rt") as file:
                content = file.read()
                self.assertEqual(content, self.html_content)

    def test_create_snapshot_failure(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "command")

            with self.assertRaises(monolith.MonolithError):
                monolith.create_snapshot("http://example.com", self.html_filepath)
