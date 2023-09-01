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
        self.assertEqual(search.filter_shared, '')

        # some params
        mock_request.GET = {
            'q': 'search query',
            'user': 'user123',
        }

        bookmark_search = BookmarkSearch.from_request(mock_request)
        self.assertEqual(bookmark_search.q, 'search query')
        self.assertEqual(bookmark_search.sort, BookmarkSearch.SORT_ADDED_DESC)
        self.assertEqual(bookmark_search.user, 'user123')
        self.assertEqual(bookmark_search.filter_shared, '')

        # all params
        mock_request.GET = {
            'q': 'search query',
            'user': 'user123',
            'sort': BookmarkSearch.SORT_TITLE_ASC,
            'filter_shared': BookmarkSearch.FILTER_SHARED_YES,
        }

        search = BookmarkSearch.from_request(mock_request)
        self.assertEqual(search.q, 'search query')
        self.assertEqual(search.user, 'user123')
        self.assertEqual(search.sort, BookmarkSearch.SORT_TITLE_ASC)
        self.assertEqual(search.filter_shared, BookmarkSearch.FILTER_SHARED_YES)

    def test_modified_params(self):
        # no params
        bookmark_search = BookmarkSearch()
        modified_params = bookmark_search.modified_params
        self.assertEqual(len(modified_params), 0)

        # params are default values
        bookmark_search = BookmarkSearch(q='', sort=BookmarkSearch.SORT_ADDED_DESC, user='', filter_shared='')
        modified_params = bookmark_search.modified_params
        self.assertEqual(len(modified_params), 0)

        # some modified params
        bookmark_search = BookmarkSearch(q='search query', sort=BookmarkSearch.SORT_ADDED_ASC)
        modified_params = bookmark_search.modified_params
        self.assertCountEqual(modified_params, ['q', 'sort'])

        # all modified params
        bookmark_search = BookmarkSearch(q='search query', sort=BookmarkSearch.SORT_ADDED_ASC, user='user123', filter_shared=BookmarkSearch.FILTER_SHARED_YES)
        modified_params = bookmark_search.modified_params
        self.assertCountEqual(modified_params, ['q', 'sort', 'user', 'filter_shared'])
