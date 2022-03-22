from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkArchiveViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_archive_bookmark(self):
        bookmark = self.setup_bookmark()

        self.client.get(reverse('bookmarks:archive', args=[bookmark.id]))
        bookmark.refresh_from_db()

        self.assertTrue(bookmark.is_archived)

    def test_should_redirect_to_index(self):
        bookmark = self.setup_bookmark()

        response = self.client.get(reverse('bookmarks:archive', args=[bookmark.id]))

        self.assertRedirects(response, reverse('bookmarks:index'))

    def test_should_redirect_to_return_url_when_specified(self):
        bookmark = self.setup_bookmark()

        response = self.client.get(
            reverse('bookmarks:archive', args=[bookmark.id]) + '?return_url=' + reverse('bookmarks:close')
        )

        self.assertRedirects(response, reverse('bookmarks:close'))

    def test_can_only_archive_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark = self.setup_bookmark(user=other_user)

        response = self.client.get(reverse('bookmarks:archive', args=[bookmark.id]))
        bookmark.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertFalse(bookmark.is_archived)
