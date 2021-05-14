from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkUnarchiveViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_unarchive_bookmark(self):
        bookmark = self.setup_bookmark(is_archived=True)

        self.client.get(reverse('bookmarks:unarchive', args=[bookmark.id]))
        bookmark.refresh_from_db()

        self.assertFalse(bookmark.is_archived)

    def test_should_redirect_to_archive(self):
        bookmark = self.setup_bookmark()

        response = self.client.get(reverse('bookmarks:unarchive', args=[bookmark.id]))

        self.assertRedirects(response, reverse('bookmarks:archived'))

    def test_should_redirect_to_return_url_when_specified(self):
        bookmark = self.setup_bookmark()

        response = self.client.get(
            reverse('bookmarks:unarchive', args=[bookmark.id]) + '?return_url=' + reverse('bookmarks:close')
        )

        self.assertRedirects(response, reverse('bookmarks:close'))
