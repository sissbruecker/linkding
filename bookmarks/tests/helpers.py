import random

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

    def setup_bookmark(self,
                       is_archived: bool = False,
                       tags=None,
                       user: User = None,
                       url: str = '',
                       title: str = '',
                       description: str = '',
                       website_title: str = '',
                       website_description: str = '',
                       ):
        if tags is None:
            tags = []
        if user is None:
            user = self.get_or_create_test_user()
        if not url:
            unique_id = get_random_string(length=32)
            url = 'https://example.com/' + unique_id
        bookmark = Bookmark(
            url=url,
            title=title,
            description=description,
            website_title=website_title,
            website_description=website_description,
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

    def setup_tag(self, user: User = None, name: str = ''):
        if user is None:
            user = self.get_or_create_test_user()
        if not name:
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


_words = [
    'quasi',
    'consequatur',
    'necessitatibus',
    'debitis',
    'quod',
    'vero',
    'qui',
    'commodi',
    'quod',
    'odio',
    'aliquam',
    'veniam',
    'architecto',
    'consequatur',
    'autem',
    'qui',
    'iste',
    'asperiores',
    'soluta',
    'et',
]


def random_sentence(num_words: int = None, including_word: str = ''):
    if num_words is None:
        num_words = random.randint(5, 10)
    selected_words = random.choices(_words, k=num_words)
    if including_word:
        selected_words.append(including_word)
    random.shuffle(selected_words)

    return ' '.join(selected_words)
