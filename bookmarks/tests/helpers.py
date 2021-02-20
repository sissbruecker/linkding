from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.test import APITestCase

from bookmarks.models import Bookmark, Tag


class BookmarkFactoryMixin:
    user = None

    def get_or_create_test_user(self):
        if self.user is None:
            self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')

        return self.user

    def setup_bookmark(self, is_archived: bool = False, tags: [Tag] = [], user: User = None):
        if user is None:
            user = self.get_or_create_test_user()
        unique_id = get_random_string(length=32)
        bookmark = Bookmark(
            url='https://example.com/' + unique_id,
            date_added=timezone.now(),
            date_modified=timezone.now(),
            owner=user,
            is_archived=is_archived
        )
        bookmark.save()
        for tag in tags:
            bookmark.tags.add(tag)
        bookmark.save()
        return bookmark

    def setup_tag(self, user: User = None):
        if user is None:
            user = self.get_or_create_test_user()
        name = get_random_string(length=32)
        tag = Tag(name=name, date_added=timezone.now(), owner=user)
        tag.save()
        return tag


class LinkdingApiTestCase(APITestCase):
    def get(self, url, expected_status_code=status.HTTP_200_OK):
        response = self.client.get(url)
        self.assertEqual(response.status_code, expected_status_code)
        return response

    def post(self, url, data=None, expected_status_code=status.HTTP_200_OK):
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, expected_status_code)
        return response

    def put(self, url, data=None, expected_status_code=status.HTTP_200_OK):
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, expected_status_code)
        return response

    def delete(self, url, expected_status_code=status.HTTP_200_OK):
        response = self.client.delete(url)
        self.assertEqual(response.status_code, expected_status_code)
        return response
