import datetime
import email
import importlib
import os
import urllib.parse

from django.test import TestCase, override_settings
from django.urls import reverse, include, resolvers
from django.urls.resolvers import URLResolver, RegexPattern
from django.conf import settings


class ContextPathTestCase(TestCase):

    def setUp(self):
        self.bookmarks_urls = importlib.import_module('bookmarks.urls')
        self.siteroot_urls = importlib.import_module('siteroot.urls')

    @override_settings(LD_CONTEXT_PATH=None)
    def tearDown(self):
        importlib.reload(self.bookmarks_urls)
        importlib.reload(self.siteroot_urls)

    @override_settings(LD_CONTEXT_PATH='linkding/')
    def test_route_with_context_path(self):
        bookmarks_patterns = importlib.reload(self.bookmarks_urls).urlpatterns
        bookmarks_match = bookmarks_patterns[0].resolve('linkding/bookmarks')
        self.assertEqual(bookmarks_match.url_name, 'index')

        siteroot_patterns = importlib.reload(self.siteroot_urls).urlpatterns
        siteroot_match = siteroot_patterns[0].resolve('linkding/login/')
        self.assertEqual(siteroot_match.url_name, 'login')

    @override_settings(LD_CONTEXT_PATH='')
    def test_route_without_context_path(self):
        bookmarks_patterns = importlib.reload(self.bookmarks_urls).urlpatterns
        bookmarks_match = bookmarks_patterns[0].resolve('bookmarks')
        self.assertEqual(bookmarks_match.url_name, 'index')

        siteroot_patterns = importlib.reload(self.siteroot_urls).urlpatterns
        siteroot_match = siteroot_patterns[0].resolve('login/')
        self.assertEqual(siteroot_match.url_name, 'login')
