import importlib

from django.test import TestCase, override_settings
from django.urls import reverse


class MockUrlConf:
    def __init__(self, module):
        self.urlpatterns = module.urlpatterns


class ContextPathTestCase(TestCase):

    def setUp(self):
        self.urls_module = importlib.import_module("bookmarks.urls")

    @override_settings(LD_CONTEXT_PATH=None)
    def tearDown(self):
        importlib.reload(self.urls_module)

    @override_settings(LD_CONTEXT_PATH="linkding/")
    def test_route_with_context_path(self):
        module = importlib.reload(self.urls_module)
        # pass mock config instead of actual module to prevent caching the
        # url config in django.urls.reverse
        urlconf = MockUrlConf(module)
        test_cases = [
            ("linkding:bookmarks.index", "/linkding/bookmarks"),
            ("linkding:bookmark-list", "/linkding/api/bookmarks/"),
            ("login", "/linkding/login/"),
            (
                "admin:bookmarks_bookmark_changelist",
                "/linkding/admin/bookmarks/bookmark/",
            ),
        ]

        for url_name, expected_url in test_cases:
            url = reverse(url_name, urlconf=urlconf)
            self.assertEqual(expected_url, url)

    @override_settings(LD_CONTEXT_PATH="")
    def test_route_without_context_path(self):
        module = importlib.reload(self.urls_module)
        # pass mock config instead of actual module to prevent caching the
        # url config in django.urls.reverse
        urlconf = MockUrlConf(module)
        test_cases = [
            ("linkding:bookmarks.index", "/bookmarks"),
            ("linkding:bookmark-list", "/api/bookmarks/"),
            ("login", "/login/"),
            ("admin:bookmarks_bookmark_changelist", "/admin/bookmarks/bookmark/"),
        ]

        for url_name, expected_url in test_cases:
            url = reverse(url_name, urlconf=urlconf)
            self.assertEqual(expected_url, url)
