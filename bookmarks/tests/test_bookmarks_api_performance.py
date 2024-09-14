from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from bookmarks.models import GlobalSettings
from bookmarks.tests.helpers import LinkdingApiTestCase, BookmarkFactoryMixin


class BookmarksApiPerformanceTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        self.api_token = Token.objects.get_or_create(
            user=self.get_or_create_test_user()
        )[0]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.api_token.key)

        # create global settings
        GlobalSettings.get()

    def get_connection(self):
        return connections[DEFAULT_DB_ALIAS]

    def test_list_bookmarks_max_queries(self):
        # set up some bookmarks with associated tags
        num_initial_bookmarks = 10
        for _ in range(num_initial_bookmarks):
            self.setup_bookmark(tags=[self.setup_tag()])

        # capture number of queries
        context = CaptureQueriesContext(self.get_connection())
        with context:
            self.get(
                reverse("bookmarks:bookmark-list"),
                expected_status_code=status.HTTP_200_OK,
            )

        number_of_queries = context.final_queries

        self.assertLess(number_of_queries, num_initial_bookmarks)

    def test_list_archived_bookmarks_max_queries(self):
        # set up some bookmarks with associated tags
        num_initial_bookmarks = 10
        for _ in range(num_initial_bookmarks):
            self.setup_bookmark(is_archived=True, tags=[self.setup_tag()])

        # capture number of queries
        context = CaptureQueriesContext(self.get_connection())
        with context:
            self.get(
                reverse("bookmarks:bookmark-archived"),
                expected_status_code=status.HTTP_200_OK,
            )

        number_of_queries = context.final_queries

        self.assertLess(number_of_queries, num_initial_bookmarks)

    def test_list_shared_bookmarks_max_queries(self):
        # set up some bookmarks with associated tags
        share_user = self.setup_user(enable_sharing=True)
        num_initial_bookmarks = 10
        for _ in range(num_initial_bookmarks):
            self.setup_bookmark(user=share_user, shared=True, tags=[self.setup_tag()])

        # capture number of queries
        context = CaptureQueriesContext(self.get_connection())
        with context:
            self.get(
                reverse("bookmarks:bookmark-shared"),
                expected_status_code=status.HTTP_200_OK,
            )

        number_of_queries = context.final_queries

        self.assertLess(number_of_queries, num_initial_bookmarks)
