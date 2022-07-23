from collections import OrderedDict

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from bookmarks.models import Bookmark
from bookmarks.tests.helpers import LinkdingApiTestCase, BookmarkFactoryMixin


class BookmarksApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        self.api_token = Token.objects.get_or_create(user=self.get_or_create_test_user())[0]
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.api_token.key)
        self.tag1 = self.setup_tag()
        self.tag2 = self.setup_tag()
        self.bookmark1 = self.setup_bookmark(tags=[self.tag1, self.tag2])
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
            expectation['website_title'] = bookmark.website_title
            expectation['website_description'] = bookmark.website_description
            expectation['is_archived'] = bookmark.is_archived
            expectation['unread'] = bookmark.unread
            expectation['tag_names'] = tag_names
            expectation['date_added'] = bookmark.date_added.isoformat().replace('+00:00', 'Z')
            expectation['date_modified'] = bookmark.date_modified.isoformat().replace('+00:00', 'Z')
            expectations.append(expectation)

        for data in data_list:
            data['tag_names'].sort(key=str.lower)

        self.assertCountEqual(data_list, expectations)

    def test_create_bookmark(self):
        data = {
            'url': 'https://example.com/',
            'title': 'Test title',
            'description': 'Test description',
            'is_archived': False,
            'unread': False,
            'tag_names': ['tag1', 'tag2']
        }
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertEqual(bookmark.url, data['url'])
        self.assertEqual(bookmark.title, data['title'])
        self.assertEqual(bookmark.description, data['description'])
        self.assertFalse(bookmark.is_archived, data['is_archived'])
        self.assertFalse(bookmark.unread, data['unread'])
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

    def test_list_bookmarks(self):
        response = self.get(reverse('bookmarks:bookmark-list'), expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], [self.bookmark1, self.bookmark2, self.bookmark3])

    def test_list_bookmarks_should_filter_by_query(self):
        response = self.get(reverse('bookmarks:bookmark-list') + '?q=#' + self.tag1.name, expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], [self.bookmark1])

    def test_list_archived_bookmarks_does_not_return_unarchived_bookmarks(self):
        response = self.get(reverse('bookmarks:bookmark-archived'), expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], [self.archived_bookmark1, self.archived_bookmark2])

    def test_list_archived_bookmarks_should_filter_by_query(self):
        response = self.get(reverse('bookmarks:bookmark-archived') + '?q=#' + self.tag1.name, expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual(response.data['results'], [self.archived_bookmark1])

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
        data = {
            'url': 'https://example.com/',
        }
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertFalse(bookmark.is_archived)

    def test_create_unread_bookmark(self):
        data = {
            'url': 'https://example.com/',
            'unread': True,
        }
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertTrue(bookmark.unread)

    def test_create_bookmark_is_not_unread_by_default(self):
        data = {
            'url': 'https://example.com/',
        }
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertFalse(bookmark.unread)

    def test_create_bookmark_minimal_payload_does_not_archive(self):
        data = {'url': 'https://example.com/'}
        self.post(reverse('bookmarks:bookmark-list'), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data['url'])
        self.assertFalse(bookmark.is_archived)

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
        self.assertEqual(updated_bookmark.tag_names, [])

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

    def test_can_only_access_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        inaccessible_bookmark = self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user, is_archived=True)

        url = reverse('bookmarks:bookmark-list')
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

        url = reverse('bookmarks:bookmark-archived')
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_bookmark.id])
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_bookmark.id])
        self.put(url, {url: 'https://example.com/'}, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-detail', args=[inaccessible_bookmark.id])
        self.delete(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-archive', args=[inaccessible_bookmark.id])
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse('bookmarks:bookmark-unarchive', args=[inaccessible_bookmark.id])
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)
