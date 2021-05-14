from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkRemoveViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_delete_bookmark(self):
        bookmark = self.setup_bookmark()

        self.client.get(reverse('bookmarks:remove', args=[bookmark.id]))

        self.assertEqual(Bookmark.objects.count(), 0)

    def test_should_redirect_to_index(self):
        bookmark = self.setup_bookmark()

        response = self.client.get(reverse('bookmarks:remove', args=[bookmark.id]))

        self.assertRedirects(response, reverse('bookmarks:index'))

    def test_should_redirect_to_return_url_when_specified(self):
        bookmark = self.setup_bookmark()

        response = self.client.get(
            reverse('bookmarks:remove', args=[bookmark.id]) + '?return_url=' + reverse('bookmarks:close')
        )

        self.assertRedirects(response, reverse('bookmarks:close'))
