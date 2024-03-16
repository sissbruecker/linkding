from django.test import TestCase

from bookmarks.models import BookmarkSearch, BookmarkSearchForm
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkSearchFormTest(TestCase, BookmarkFactoryMixin):
    def test_initial_values(self):
        # no params
        search = BookmarkSearch()
        form = BookmarkSearchForm(search)
        self.assertEqual(form["q"].initial, "")
        self.assertEqual(form["user"].initial, "")
        self.assertEqual(form["sort"].initial, BookmarkSearch.SORT_ADDED_DESC)
        self.assertEqual(form["shared"].initial, BookmarkSearch.FILTER_SHARED_OFF)
        self.assertEqual(form["unread"].initial, BookmarkSearch.FILTER_UNREAD_OFF)

        # with params
        search = BookmarkSearch(
            q="search query",
            sort=BookmarkSearch.SORT_ADDED_ASC,
            user="user123",
            shared=BookmarkSearch.FILTER_SHARED_SHARED,
            unread=BookmarkSearch.FILTER_UNREAD_YES,
        )
        form = BookmarkSearchForm(search)
        self.assertEqual(form["q"].initial, "search query")
        self.assertEqual(form["user"].initial, "user123")
        self.assertEqual(form["sort"].initial, BookmarkSearch.SORT_ADDED_ASC)
        self.assertEqual(form["shared"].initial, BookmarkSearch.FILTER_SHARED_SHARED)
        self.assertEqual(form["unread"].initial, BookmarkSearch.FILTER_UNREAD_YES)

    def test_user_options(self):
        users = [
            self.setup_user("user1"),
            self.setup_user("user2"),
            self.setup_user("user3"),
        ]
        search = BookmarkSearch()
        form = BookmarkSearchForm(search, users=users)

        self.assertCountEqual(
            form["user"].field.choices,
            [
                ("", "Everyone"),
                ("user1", "user1"),
                ("user2", "user2"),
                ("user3", "user3"),
            ],
        )

    def test_hidden_fields(self):
        # no modified params
        search = BookmarkSearch()
        form = BookmarkSearchForm(search)
        self.assertEqual(len(form.hidden_fields()), 0)

        # some modified params
        search = BookmarkSearch(q="search query", sort=BookmarkSearch.SORT_ADDED_ASC)
        form = BookmarkSearchForm(search)
        self.assertCountEqual(form.hidden_fields(), [form["q"], form["sort"]])

        # all modified params
        search = BookmarkSearch(
            q="search query",
            sort=BookmarkSearch.SORT_ADDED_ASC,
            user="user123",
            shared=BookmarkSearch.FILTER_SHARED_SHARED,
            unread=BookmarkSearch.FILTER_UNREAD_YES,
        )
        form = BookmarkSearchForm(search)
        self.assertCountEqual(
            form.hidden_fields(),
            [form["q"], form["sort"], form["user"], form["shared"], form["unread"]],
        )

        # some modified params are editable fields
        search = BookmarkSearch(
            q="search query", sort=BookmarkSearch.SORT_ADDED_ASC, user="user123"
        )
        form = BookmarkSearchForm(search, editable_fields=["q", "user"])
        self.assertCountEqual(form.hidden_fields(), [form["sort"]])
