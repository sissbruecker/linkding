from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from bookmarks.models import FeedToken, GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin


class FeedsPerformanceTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)
        self.token = FeedToken.objects.get_or_create(user=user)[0]

        # create global settings
        GlobalSettings.get()

    def get_connection(self):
        return connections[DEFAULT_DB_ALIAS]

    def test_all_max_queries(self):
        # set up some bookmarks with associated tags
        num_initial_bookmarks = 10
        for _ in range(num_initial_bookmarks):
            self.setup_bookmark(tags=[self.setup_tag()])

        # capture number of queries
        context = CaptureQueriesContext(self.get_connection())
        with context:
            feed_url = reverse("bookmarks:feeds.all", args=[self.token.key])
            self.client.get(feed_url)

        number_of_queries = context.final_queries

        self.assertLess(number_of_queries, num_initial_bookmarks)
