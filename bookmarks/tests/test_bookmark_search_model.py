from unittest.mock import Mock
from bookmarks.models import BookmarkSearch
from django.test import TestCase


class BookmarkSearchModelTest(TestCase):
    def test_from_request(self):
        # no params
        mock_request = Mock()
        mock_request.GET = {}

        search = BookmarkSearch.from_request(mock_request)
        self.assertEqual(search.q, '')
        self.assertEqual(search.sort, BookmarkSearch.SORT_ADDED_DESC)
        self.assertEqual(search.user, '')
        self.assertEqual(search.shared, '')
        self.assertEqual(search.unread, '')

        # some params
        mock_request.GET = {
            'q': 'search query',
            'user': 'user123',
        }

        bookmark_search = BookmarkSearch.from_request(mock_request)
        self.assertEqual(bookmark_search.q, 'search query')
        self.assertEqual(bookmark_search.sort, BookmarkSearch.SORT_ADDED_DESC)
        self.assertEqual(bookmark_search.user, 'user123')
        self.assertEqual(bookmark_search.shared, '')
        self.assertEqual(bookmark_search.unread, '')

        # all params
        mock_request.GET = {
            'q': 'search query',
            'user': 'user123',
            'sort': BookmarkSearch.SORT_TITLE_ASC,
            'shared': BookmarkSearch.FILTER_SHARED_SHARED,
            'unread': BookmarkSearch.FILTER_UNREAD_YES,
        }

        search = BookmarkSearch.from_request(mock_request)
        self.assertEqual(search.q, 'search query')
        self.assertEqual(search.user, 'user123')
        self.assertEqual(search.sort, BookmarkSearch.SORT_TITLE_ASC)
        self.assertEqual(search.shared, BookmarkSearch.FILTER_SHARED_SHARED)
        self.assertEqual(search.unread, BookmarkSearch.FILTER_UNREAD_YES)

    def test_modified_params(self):
        # no params
        bookmark_search = BookmarkSearch()
        modified_params = bookmark_search.modified_params
        self.assertEqual(len(modified_params), 0)

        # params are default values
        bookmark_search = BookmarkSearch(q='', sort=BookmarkSearch.SORT_ADDED_DESC, user='', shared='')
        modified_params = bookmark_search.modified_params
        self.assertEqual(len(modified_params), 0)

        # some modified params
        bookmark_search = BookmarkSearch(q='search query', sort=BookmarkSearch.SORT_ADDED_ASC)
        modified_params = bookmark_search.modified_params
        self.assertCountEqual(modified_params, ['q', 'sort'])

        # all modified params
        bookmark_search = BookmarkSearch(q='search query',
                                         sort=BookmarkSearch.SORT_ADDED_ASC,
                                         user='user123',
                                         shared=BookmarkSearch.FILTER_SHARED_SHARED,
                                         unread=BookmarkSearch.FILTER_UNREAD_YES)
        modified_params = bookmark_search.modified_params
        self.assertCountEqual(modified_params, ['q', 'sort', 'user', 'shared', 'unread'])

    def test_has_modifications(self):
        # no params
        bookmark_search = BookmarkSearch()
        self.assertFalse(bookmark_search.has_modifications)

        # params are default values
        bookmark_search = BookmarkSearch(q='', sort=BookmarkSearch.SORT_ADDED_DESC, user='', shared='')
        self.assertFalse(bookmark_search.has_modifications)

        # modified params
        bookmark_search = BookmarkSearch(q='search query', sort=BookmarkSearch.SORT_ADDED_ASC)
        self.assertTrue(bookmark_search.has_modifications)
