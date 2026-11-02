import os
import subprocess
import tempfile
from unittest import mock

from django.test import TestCase, override_settings

from bookmarks.services import singlefile


class SingleFileServiceTestCase(TestCase):
    def setUp(self):
        self.temp_html_filepath = None

    def tearDown(self):
        if self.temp_html_filepath and os.path.exists(self.temp_html_filepath):
            os.remove(self.temp_html_filepath)

    def create_test_file(self, *args, **kwargs):
        self.temp_html_filepath = tempfile.mkstemp(suffix=".tmp")[1]

    def test_create_snapshot_failure(self):
        # subprocess fails - which it probably doesn't as single-file doesn't return exit codes
        with mock.patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = subprocess.CalledProcessError(1, "command")

            with self.assertRaises(singlefile.SingleFileError):
                singlefile.create_snapshot("http://example.com", "nonexistentfile.tmp")

        # so also check that it raises error if output file isn't created
        with (
            mock.patch("subprocess.Popen"),
            self.assertRaises(singlefile.SingleFileError),
        ):
            singlefile.create_snapshot("http://example.com", "nonexistentfile.tmp")

    def _mock_proxy(self):
        proxy_ctx = mock.Mock()
        proxy_ctx.__enter__ = mock.Mock(return_value=18080)
        proxy_ctx.__exit__ = mock.Mock(return_value=False)
        return proxy_ctx

    def test_create_snapshot_empty_options(self):
        mock_process = mock.Mock()
        mock_process.wait.return_value = 0
        self.create_test_file()

        with (
            mock.patch(
                "bookmarks.services.ssrf_proxy.egress_proxy",
                return_value=self._mock_proxy(),
            ),
            mock.patch("subprocess.Popen") as mock_popen,
        ):
            singlefile.create_snapshot("http://example.com", self.temp_html_filepath)

            expected_args = [
                "single-file",
                '--browser-arg="--headless=new"',
                '--browser-arg="--user-data-dir=./chromium-profile"',
                '--browser-arg="--no-sandbox"',
                '--browser-arg="--load-extension=uBOLite.chromium.mv3"',
                '--browser-arg="--proxy-server=http://127.0.0.1:18080"',
                '--browser-arg="--proxy-bypass-list=<-loopback>"',
                "http://example.com",
                self.temp_html_filepath,
            ]
            mock_popen.assert_called_with(expected_args, start_new_session=True)

    @override_settings(
        LD_SINGLEFILE_OPTIONS='--some-option "some value" --another-option "another value" --third-option="third value"'
    )
    def test_create_snapshot_custom_options(self):
        mock_process = mock.Mock()
        mock_process.wait.return_value = 0
        self.create_test_file()

        with (
            mock.patch(
                "bookmarks.services.ssrf_proxy.egress_proxy",
                return_value=self._mock_proxy(),
            ),
            mock.patch("subprocess.Popen") as mock_popen,
        ):
            singlefile.create_snapshot("http://example.com", self.temp_html_filepath)

            expected_args = [
                "single-file",
                '--browser-arg="--headless=new"',
                '--browser-arg="--user-data-dir=./chromium-profile"',
                '--browser-arg="--no-sandbox"',
                '--browser-arg="--load-extension=uBOLite.chromium.mv3"',
                "--some-option",
                "some value",
                "--another-option",
                "another value",
                "--third-option=third value",
                '--browser-arg="--proxy-server=http://127.0.0.1:18080"',
                '--browser-arg="--proxy-bypass-list=<-loopback>"',
                "http://example.com",
                self.temp_html_filepath,
            ]
            mock_popen.assert_called_with(expected_args, start_new_session=True)

    def test_create_snapshot_default_timeout_setting(self):
        mock_process = mock.Mock()
        mock_process.wait.return_value = 0
        self.create_test_file()

        with mock.patch("subprocess.Popen", return_value=mock_process):
            singlefile.create_snapshot("http://example.com", self.temp_html_filepath)

            mock_process.wait.assert_called_with(timeout=120)

    @override_settings(LD_SINGLEFILE_TIMEOUT_SEC=180)
    def test_create_snapshot_custom_timeout_setting(self):
        mock_process = mock.Mock()
        mock_process.wait.return_value = 0
        self.create_test_file()

        with mock.patch("subprocess.Popen", return_value=mock_process):
            singlefile.create_snapshot("http://example.com", self.temp_html_filepath)

            mock_process.wait.assert_called_with(timeout=180)
