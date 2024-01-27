import importlib
import os
from unittest import mock

from django.test import TestCase


class AppOptionsTestCase(TestCase):
    def setUp(self) -> None:
        self.settings_module = importlib.import_module("siteroot.settings.base")

    def test_empty_csrf_trusted_origins(self):
        module = importlib.reload(self.settings_module)

        self.assertFalse(hasattr(module, "CSRF_TRUSTED_ORIGINS"))

    @mock.patch.dict(
        os.environ, {"LD_CSRF_TRUSTED_ORIGINS": "https://linkding.example.com"}
    )
    def test_single_csrf_trusted_origin(self):
        module = importlib.reload(self.settings_module)

        self.assertTrue(hasattr(module, "CSRF_TRUSTED_ORIGINS"))
        self.assertCountEqual(
            module.CSRF_TRUSTED_ORIGINS, ["https://linkding.example.com"]
        )

    @mock.patch.dict(
        os.environ,
        {
            "LD_CSRF_TRUSTED_ORIGINS": "https://linkding.example.com,http://linkding.example.com"
        },
    )
    def test_multiple_csrf_trusted_origin(self):
        module = importlib.reload(self.settings_module)

        self.assertTrue(hasattr(module, "CSRF_TRUSTED_ORIGINS"))
        self.assertCountEqual(
            module.CSRF_TRUSTED_ORIGINS,
            ["https://linkding.example.com", "http://linkding.example.com"],
        )
