from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from bookmarks.models import GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkSharedViewPerformanceTestCase(TransactionTestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def get_connection(self):
        return connections[DEFAULT_DB_ALIAS]

    def test_should_not_increase_number_of_queries_per_bookmark(self):
        # create global settings
        GlobalSettings.get()

        # create initial users and bookmarks
        num_initial_bookmarks = 10
        for _ in range(num_initial_bookmarks):
            user = self.setup_user(enable_sharing=True)
            self.setup_bookmark(user=user, shared=True)

        # capture number of queries
        context = CaptureQueriesContext(self.get_connection())
        with context:
            response = self.client.get(reverse("bookmarks:shared"))
            self.assertContains(
                response, '<li ld-bookmark-item class="shared">', num_initial_bookmarks
            )

        number_of_queries = context.final_queries

        # add more users and bookmarks
        num_additional_bookmarks = 10
        for _ in range(num_additional_bookmarks):
            user = self.setup_user(enable_sharing=True)
            self.setup_bookmark(user=user, shared=True)

        # assert num queries doesn't increase
        with self.assertNumQueries(number_of_queries):
            response = self.client.get(reverse("bookmarks:shared"))
            self.assertContains(
                response,
                '<li ld-bookmark-item class="shared">',
                num_initial_bookmarks + num_additional_bookmarks,
            )
