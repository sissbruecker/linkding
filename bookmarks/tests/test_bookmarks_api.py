import urllib.parse
from collections import OrderedDict
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from bookmarks.models import Bookmark
from bookmarks.services import website_loader
from bookmarks.services.website_loader import WebsiteMetadata
from bookmarks.tests.helpers import LinkdingApiTestCase, BookmarkFactoryMixin


class BookmarksApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        self.api_token = Token.objects.get_or_create(user=self.get_or_create_test_user())[0]
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.api_token.key)
        self.tag1 = self.setup_tag()
        self.tag2 = self.setup_tag()
        self.bookmark1 = self.setup_bookmark(tags=[self.tag1, self.tag2], notes='Test notes')
        self.bookmark2 = self.setup_bookmark()
        self.bookmark3 = self.setup_bookmark(tags=[self.tag2])
        self.archived_bookmark1 = self.setup_bookmark(is_archived=True, tags=[self.tag1, self.tag2])
        self.archived_bookmark2 = self.setup_bookmark(is_archived=True)

    def assertBookmarkListEqual(self, data_list, bookmarks):
        expectations = []
        for bookmark in bookmarks:
            tag_names = [tag.name for tag in bookmark.tags.all()]
            tag_names.sort(key=str.lower)
            expectation = OrderedDict()
            expectation['id'] = bookmark.id
            expectation['url'] = bookmark.url
            expectation['title'] = bookmark.title
            expectation['description'] = bookmark.description
            expectation['notes'] = bookmark.notes
            expectation['website_title'] = bookmark.website_title
            expectation['website_description'] = bookmark.website_description
            expectation['is_archived'] = bookmark.is_archived
            expectation['unread'] = bookmark.unread
            expectation['shared'] = bookmark.shared
            expectation['tag_names'] = tag_names
            expectation['date_added'] = bookmark.date_added.isoformat().replace('+00:00', 'Z')
            expectation['date_modified'] = bookmark.date_modified.isoformat().replace('+00:00', 'Z')
            expectations.append(expectation)

        for data in data_list:
            data['tag_names'].sort(key=str.lower)

        self.assertCountEqual(data_list, expectations)

    def test_list_bookmarks(self):
        response = self.get(reverse('bookmarks:bookmark-list'), expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], [self.bookmark1, self.bookmark2, self.bookmark3])

    def test_list_bookmarks_should_filter_by_query(self):
        response = self.get(reverse('bookmarks:bookmark-list') + '?q=#' + self.tag1.name,
                            expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], [self.bookmark1])

    def test_list_archived_bookmarks_does_not_return_unarchived_bookmarks(self):
        response = self.get(reverse('bookmarks:bookmark-archived'), expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], [self.archived_bookmark1, self.archived_bookmark2])

    def test_list_archived_bookmarks_should_filter_by_query(self):
        response = self.get(reverse('bookmarks:bookmark-archived') + '?q=#' + self.tag1.name,
                            expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], [self.archived_bookmark1])

    def test_list_shared_bookmarks(self):
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        user4 = self.setup_user(enable_sharing=False)
        shared_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user2),
            self.setup_bookmark(shared=True, user=user3),
        ]
        # Unshared bookmarks
        self.setup_bookmark(shared=False, user=user1)
        self.setup_bookmark(shared=False, user=user2)
        self.setup_bookmark(shared=False, user=user3)
        self.setup_bookmark(shared=True, user=user4)

        response = self.get(reverse('bookmarks:bookmark-shared'), expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], shared_bookmarks)

    def test_list_shared_bookmarks_should_filter_by_query_and_user(self):
        # Search by query
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        expected_bookmarks = [
            self.setup_bookmark(title='searchvalue', shared=True, user=user1),
            self.setup_bookmark(title='searchvalue', shared=True, user=user2),
            self.setup_bookmark(title='searchvalue', shared=True, user=user3),
        ]
        self.setup_bookmark(shared=True, user=user1),
        self.setup_bookmark(shared=True, user=user2),
        self.setup_bookmark(shared=True, user=user3),

        response = self.get(reverse('bookmarks:bookmark-shared') + '?q=searchvalue',
                            expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], expected_bookmarks)

        # Search by user
        user_search_user = self.setup_user(enable_sharing=True)
        expected_bookmarks = [
            self.setup_bookmark(shared=True, user=user_search_user),
            self.setup_bookmark(shared=True, user=user_search_user),
            self.setup_bookmark(shared=True, user=user_search_user),
        ]
        response = self.get(reverse('bookmarks:bookmark-shared') + '?user=' + user_search_user.username,
                            expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], expected_bookmarks)

        # Search by query and user
        combined_search_user = self.setup_user(enable_sharing=True)
        expected_bookmarks = [
            self.setup_bookmark(title='searchvalue', shared=True, user=combined_search_user),
            self.setup_bookmark(title='searchvalue', shared=True, user=combined_search_user),
            self.setup_bookmark(title='searchvalue', shared=True, user=combined_search_user),
        ]
        response = self.get(
            reverse('bookmarks:bookmark-shared') + '?q=searchvalue&user=' + combined_search_user.username,
            expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], expected_bookmarks)

    def test_create_bookmark(self):
        data = {
            'url': 'https://example.com/',
            'title': 'Test title',
            'description': 'Test description',
            'notes': 'Test notes',
            'is_archived': False,
            'unread': False,
            'shared': False,
            'tag_names': ['tag1', 'tag2']
        }
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertEqual(bookmark.url, data['url'])
        self.assertEqual(bookmark.title, data['title'])
        self.assertEqual(bookmark.description, data['description'])
        self.assertEqual(bookmark.notes, data['notes'])
        self.assertFalse(bookmark.is_archived, data['is_archived'])
        self.assertFalse(bookmark.unread, data['unread'])
        self.assertFalse(bookmark.shared, data['shared'])
        self.assertEqual(bookmark.tags.count(), 2)
        self.assertEqual(bookmark.tags.filter(name=data['tag_names'][0]).count(), 1)
        self.assertEqual(bookmark.tags.filter(name=data['tag_names'][1]).count(), 1)

    def test_create_bookmark_with_same_url_updates_existing_bookmark(self):
        original_bookmark = self.setup_bookmark()
        data = {
            'url': original_bookmark.url,
            'title': 'Updated title',
            'description': 'Updated description',
            'notes': 'Updated notes',
            'unread': True,
            'shared': True,
            'is_archived': True,
            'tag_names': ['tag1', 'tag2']
        }
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertEqual(bookmark.id, original_bookmark.id)
        self.assertEqual(bookmark.url, data['url'])
        self.assertEqual(bookmark.title, data['title'])
        self.assertEqual(bookmark.description, data['description'])
        self.assertEqual(bookmark.notes, data['notes'])
        # Saving a duplicate bookmark should not modify archive flag - right?
        self.assertFalse(bookmark.is_archived)
        self.assertEqual(bookmark.unread, data['unread'])
        self.assertEqual(bookmark.shared, data['shared'])
        self.assertEqual(bookmark.tags.count(), 2)
        self.assertEqual(bookmark.tags.filter(name=data['tag_names'][0]).count(), 1)
        self.assertEqual(bookmark.tags.filter(name=data['tag_names'][1]).count(), 1)

    def test_create_bookmark_replaces_whitespace_in_tag_names(self):
        data = {
            'url': 'https://example.com/',
            'title': 'Test title',
            'description': 'Test description',
            'tag_names': ['tag 1', 'tag 2']
        }
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        tag_names = [tag.name for tag in bookmark.tags.all()]
        self.assertListEqual(tag_names, ['tag-1', 'tag-2'])

    def test_create_bookmark_minimal_payload(self):
        data = {'url': 'https://example.com/'}
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)

    def test_create_archived_bookmark(self):
        data = {
            'url': 'https://example.com/',
            'title': 'Test title',
            'description': 'Test description',
            'is_archived': True,
            'tag_names': ['tag1', 'tag2']
        }
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertEqual(bookmark.url, data['url'])
        self.assertEqual(bookmark.title, data['title'])
        self.assertEqual(bookmark.description, data['description'])
        self.assertTrue(bookmark.is_archived)
        self.assertEqual(bookmark.tags.count(), 2)
        self.assertEqual(bookmark.tags.filter(name=data['tag_names'][0]).count(), 1)
        self.assertEqual(bookmark.tags.filter(name=data['tag_names'][1]).count(), 1)

    def test_create_bookmark_is_not_archived_by_default(self):
        data = {'url': 'https://example.com/'}
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertFalse(bookmark.is_archived)

    def test_create_unread_bookmark(self):
        data = {'url': 'https://example.com/', 'unread': True}
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertTrue(bookmark.unread)

    def test_create_bookmark_is_not_unread_by_default(self):
        data = {'url': 'https://example.com/'}
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertFalse(bookmark.unread)

    def test_create_shared_bookmark(self):
        data = {'url': 'https://example.com/', 'shared': True}
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertTrue(bookmark.shared)

    def test_create_bookmark_is_not_shared_by_default(self):
        data = {'url': 'https://example.com/'}
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertFalse(bookmark.shared)

    def test_get_bookmark(self):
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual([response.data], [self.bookmark1])

    def test_update_bookmark(self):
        data = {'url': 'https://example.com/'}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=self.bookmark1.id)
        self.assertEqual(updated_bookmark.url, data['url'])

    def test_update_bookmark_fails_without_required_fields(self):
        data = {'title': 'https://example.com/'}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.put(url, data, expected_status_code=status.HTTP_400_BAD_REQUEST)

    def test_update_bookmark_with_minimal_payload_clears_all_fields(self):
        data = {'url': 'https://example.com/'}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=self.bookmark1.id)
        self.assertEqual(updated_bookmark.url, data['url'])
        self.assertEqual(updated_bookmark.title, '')
        self.assertEqual(updated_bookmark.description, '')
        self.assertEqual(updated_bookmark.notes, '')
        self.assertEqual(updated_bookmark.tag_names, [])

    def test_update_bookmark_unread_flag(self):
        data = {'url': 'https://example.com/', 'unread': True}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=self.bookmark1.id)
        self.assertEqual(updated_bookmark.unread, True)

    def test_update_bookmark_shared_flag(self):
        data = {'url': 'https://example.com/', 'shared': True}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=self.bookmark1.id)
        self.assertEqual(updated_bookmark.shared, True)

    def test_patch_bookmark(self):
        data = {'url': 'https://example.com'}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        self.assertEqual(self.bookmark1.url, data['url'])

        data = {'title': 'Updated title'}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        self.assertEqual(self.bookmark1.title, data['title'])

        data = {'description': 'Updated description'}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        self.assertEqual(self.bookmark1.description, data['description'])

        data = {'notes': 'Updated notes'}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        self.assertEqual(self.bookmark1.notes, data['notes'])

        data = {'unread': True}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        self.assertTrue(self.bookmark1.unread)

        data = {'unread': False}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        self.assertFalse(self.bookmark1.unread)

        data = {'shared': True}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        self.assertTrue(self.bookmark1.shared)

        data = {'shared': False}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        self.assertFalse(self.bookmark1.shared)

        data = {'tag_names': ['updated-tag-1', 'updated-tag-2']}
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        self.bookmark1.refresh_from_db()
        tag_names = [tag.name for tag in self.bookmark1.tags.all()]
        self.assertListEqual(tag_names, ['updated-tag-1', 'updated-tag-2'])

    def test_patch_with_empty_payload_does_not_modify_bookmark(self):
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.patch(url, {}, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=self.bookmark1.id)
        self.assertEqual(updated_bookmark.url, self.bookmark1.url)
        self.assertEqual(updated_bookmark.title, self.bookmark1.title)
        self.assertEqual(updated_bookmark.description, self.bookmark1.description)
        self.assertListEqual(updated_bookmark.tag_names, self.bookmark1.tag_names)

    def test_delete_bookmark(self):
        url = reverse('bookmarks:bookmark-detail', args=[self.bookmark1.id])
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(Bookmark.objects.filter(id=self.bookmark1.id)), 0)

    def test_archive(self):
        url = reverse('bookmarks:bookmark-archive', args=[self.bookmark1.id])
        self.post(url, expected_status_code=status.HTTP_204_NO_CONTENT)
        bookmark = Bookmark.objects.get(id=self.bookmark1.id)
        self.assertTrue(bookmark.is_archived)

    def test_unarchive(self):
        url = reverse('bookmarks:bookmark-unarchive', args=[self.archived_bookmark1.id])
        self.post(url, expected_status_code=status.HTTP_204_NO_CONTENT)
        bookmark = Bookmark.objects.get(id=self.archived_bookmark1.id)
        self.assertFalse(bookmark.is_archived)

    def test_check_returns_no_bookmark_if_url_is_not_bookmarked(self):
        url = reverse('bookmarks:bookmark-check')
        check_url = urllib.parse.quote_plus('https://example.com')
        response = self.get(f'{url}?url={check_url}', expected_status_code=status.HTTP_200_OK)
        bookmark_data = response.data['bookmark']

        self.assertIsNone(bookmark_data)

    def test_check_returns_scraped_metadata_if_url_is_not_bookmarked(self):
        with patch.object(website_loader, 'load_website_metadata') as mock_load_website_metadata:
            expected_metadata = WebsiteMetadata(
                'https://example.com',
                'Scraped metadata',
                'Scraped description'
            )
            mock_load_website_metadata.return_value = expected_metadata

            url = reverse('bookmarks:bookmark-check')
            check_url = urllib.parse.quote_plus('https://example.com')
            response = self.get(f'{url}?url={check_url}', expected_status_code=status.HTTP_200_OK)
            metadata = response.data['metadata']

            self.assertIsNotNone(metadata)
            self.assertIsNotNone(expected_metadata.url, metadata['url'])
            self.assertIsNotNone(expected_metadata.title, metadata['title'])
            self.assertIsNotNone(expected_metadata.description, metadata['description'])

    def test_check_returns_bookmark_if_url_is_bookmarked(self):
        bookmark = self.setup_bookmark(url='https://example.com',
                                       title='Example title',
                                       description='Example description')

        url = reverse('bookmarks:bookmark-check')
        check_url = urllib.parse.quote_plus('https://example.com')
        response = self.get(f'{url}?url={check_url}', expected_status_code=status.HTTP_200_OK)
        bookmark_data = response.data['bookmark']

        self.assertIsNotNone(bookmark_data)
        self.assertEqual(bookmark.id, bookmark_data['id'])
        self.assertEqual(bookmark.url, bookmark_data['url'])
        self.assertEqual(bookmark.title, bookmark_data['title'])
        self.assertEqual(bookmark.description, bookmark_data['description'])

    def test_check_returns_existing_metadata_if_url_is_bookmarked(self):
        bookmark = self.setup_bookmark(url='https://example.com',
                                       website_title='Existing title',
                                       website_description='Existing description')

        with patch.object(website_loader, 'load_website_metadata') as mock_load_website_metadata:
            url = reverse('bookmarks:bookmark-check')
            check_url = urllib.parse.quote_plus('https://example.com')
            response = self.get(f'{url}?url={check_url}', expected_status_code=status.HTTP_200_OK)
            metadata = response.data['metadata']

            mock_load_website_metadata.assert_not_called()
            self.assertIsNotNone(metadata)
            self.assertIsNotNone(bookmark.url, metadata['url'])
            self.assertIsNotNone(bookmark.website_title, metadata['title'])
            self.assertIsNotNone(bookmark.website_description, metadata['description'])

    def test_can_only_access_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        inaccessible_bookmark = self.setup_bookmark(user=other_user)
        inaccessible_shared_bookmark = self.setup_bookmark(user=other_user, shared=True)
        self.setup_bookmark(user=other_user, is_archived=True)

        url = reverse('bookmarks:bookmark-list')
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

        url = reverse('bookmarks:bookmark-archived')
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_bookmark.id])
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_shared_bookmark.id])
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_bookmark.id])
        self.put(url, {url: 'https://example.com/'}, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_shared_bookmark.id])
        self.put(url, {url: 'https://example.com/'}, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_bookmark.id])
        self.delete(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_shared_bookmark.id])
        self.delete(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-archive', args=[inaccessible_bookmark.id])
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-archive', args=[inaccessible_shared_bookmark.id])
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-unarchive', args=[inaccessible_bookmark.id])
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-unarchive', args=[inaccessible_shared_bookmark.id])
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-check')
        check_url = urllib.parse.quote_plus(inaccessible_bookmark.url)
        response = self.get(f'{url}?url={check_url}', expected_status_code=status.HTTP_200_OK)
        self.assertIsNone(response.data['bookmark'])
