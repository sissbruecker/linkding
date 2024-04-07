import gzip
import os
import subprocess
from unittest import mock

from django.test import TestCase

from bookmarks.services import singlefile


class SingleFileServiceTestCase(TestCase):
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
        mock_process = mock.Mock()
        mock_process.wait.return_value = 0
        self.create_test_file()

        with mock.patch("subprocess.Popen", return_value=mock_process):
            singlefile.create_snapshot("http://example.com", self.html_filepath)

            self.assertTrue(os.path.exists(self.html_filepath))
            self.assertFalse(os.path.exists(self.temp_html_filepath))

            with gzip.open(self.html_filepath, "rt") as file:
                content = file.read()
                self.assertEqual(content, self.html_content)

    def test_create_snapshot_failure(self):
        # subprocess fails - which it probably doesn't as single-file doesn't return exit codes
        with mock.patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = subprocess.CalledProcessError(1, "command")

            with self.assertRaises(singlefile.SingeFileError):
                singlefile.create_snapshot("http://example.com", self.html_filepath)

        # so also check that it raises error if output file isn't created
        with mock.patch("subprocess.Popen"):
            with self.assertRaises(singlefile.SingeFileError):
                singlefile.create_snapshot("http://example.com", self.html_filepath)
