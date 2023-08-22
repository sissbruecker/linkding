from django.contrib.auth.models import User
from django.forms import model_to_dict
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkActionViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertBookmarksAreUnmodified(self, bookmarks: [Bookmark]):
        self.assertEqual(len(bookmarks), Bookmark.objects.count())

        for bookmark in bookmarks:
            self.assertEqual(model_to_dict(bookmark), model_to_dict(Bookmark.objects.get(id=bookmark.id)))

    def test_archive_should_archive_bookmark(self):
        bookmark = self.setup_bookmark()

        self.client.post(reverse('bookmarks:action'), {
            'archive': [bookmark.id],
        })

        bookmark.refresh_from_db()

        self.assertTrue(bookmark.is_archived)

    def test_can_only_archive_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark = self.setup_bookmark(user=other_user)

        response = self.client.post(reverse('bookmarks:action'), {
            'archive': [bookmark.id],
        })

        bookmark.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertFalse(bookmark.is_archived)

    def test_unarchive_should_unarchive_bookmark(self):
        bookmark = self.setup_bookmark(is_archived=True)

        self.client.post(reverse('bookmarks:action'), {
            'unarchive': [bookmark.id],
        })
        bookmark.refresh_from_db()

        self.assertFalse(bookmark.is_archived)

    def test_unarchive_can_only_archive_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark = self.setup_bookmark(is_archived=True, user=other_user)

        response = self.client.post(reverse('bookmarks:action'), {
            'unarchive': [bookmark.id],
        })
        bookmark.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertTrue(bookmark.is_archived)

    def test_delete_should_delete_bookmark(self):
        bookmark = self.setup_bookmark()

        self.client.post(reverse('bookmarks:action'), {
            'remove': [bookmark.id],
        })

        self.assertEqual(Bookmark.objects.count(), 0)

    def test_delete_can_only_delete_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark = self.setup_bookmark(user=other_user)

        response = self.client.post(reverse('bookmarks:action'), {
            'remove': [bookmark.id],
        })
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Bookmark.objects.filter(id=bookmark.id).exists())

    def test_mark_as_read(self):
        bookmark = self.setup_bookmark(unread=True)

        self.client.post(reverse('bookmarks:action'), {
            'mark_as_read': [bookmark.id],
        })
        bookmark.refresh_from_db()

        self.assertFalse(bookmark.unread)

    def test_unshare_should_unshare_bookmark(self):
        bookmark = self.setup_bookmark(shared=True)

        self.client.post(reverse('bookmarks:action'), {
            'unshare': [bookmark.id],
        })

        bookmark.refresh_from_db()

        self.assertFalse(bookmark.shared)

    def test_can_only_unshare_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        response = self.client.post(reverse('bookmarks:action'), {
            'unshare': [bookmark.id],
        })

        bookmark.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertTrue(bookmark.shared)

    def test_bulk_archive(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_archive'],
            'bulk_execute': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_can_only_bulk_archive_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark1 = self.setup_bookmark(user=other_user)
        bookmark2 = self.setup_bookmark(user=other_user)
        bookmark3 = self.setup_bookmark(user=other_user)

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_archive'],
            'bulk_execute': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_bulk_unarchive(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_unarchive'],
            'bulk_execute': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_can_only_bulk_unarchive_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark1 = self.setup_bookmark(is_archived=True, user=other_user)
        bookmark2 = self.setup_bookmark(is_archived=True, user=other_user)
        bookmark3 = self.setup_bookmark(is_archived=True, user=other_user)

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_unarchive'],
            'bulk_execute': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_bulk_delete(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_delete'],
            'bulk_execute': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertIsNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNone(Bookmark.objects.filter(id=bookmark3.id).first())

    def test_can_only_bulk_delete_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark1 = self.setup_bookmark(user=other_user)
        bookmark2 = self.setup_bookmark(user=other_user)
        bookmark3 = self.setup_bookmark(user=other_user)

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_delete'],
            'bulk_execute': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertIsNotNone(Bookmark.objects.filter(id=bookmark1.id).first())
        self.assertIsNotNone(Bookmark.objects.filter(id=bookmark2.id).first())
        self.assertIsNotNone(Bookmark.objects.filter(id=bookmark3.id).first())

    def test_bulk_tag(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_tag'],
            'bulk_execute': [''],
            'bulk_tag_string': [f'{tag1.name} {tag2.name}'],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_can_only_bulk_tag_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark1 = self.setup_bookmark(user=other_user)
        bookmark2 = self.setup_bookmark(user=other_user)
        bookmark3 = self.setup_bookmark(user=other_user)
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_tag'],
            'bulk_execute': [''],
            'bulk_tag_string': [f'{tag1.name} {tag2.name}'],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [])

    def test_bulk_untag(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2])
        bookmark3 = self.setup_bookmark(tags=[tag1, tag2])

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_untag'],
            'bulk_execute': [''],
            'bulk_tag_string': [f'{tag1.name} {tag2.name}'],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [])
        self.assertCountEqual(bookmark2.tags.all(), [])
        self.assertCountEqual(bookmark3.tags.all(), [])

    def test_can_only_bulk_untag_own_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[tag1, tag2], user=other_user)
        bookmark2 = self.setup_bookmark(tags=[tag1, tag2], user=other_user)
        bookmark3 = self.setup_bookmark(tags=[tag1, tag2], user=other_user)

        self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_untag'],
            'bulk_execute': [''],
            'bulk_tag_string': [f'{tag1.name} {tag2.name}'],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_handles_empty_bookmark_id(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        response = self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_archive'],
            'bulk_execute': [''],
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.post(reverse('bookmarks:action'), {
            'bulk_action': ['bulk_archive'],
            'bulk_execute': [''],
            'bookmark_id': [],
        })
        self.assertEqual(response.status_code, 302)

        self.assertBookmarksAreUnmodified([bookmark1, bookmark2, bookmark3])

    def test_empty_action_does_not_modify_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(reverse('bookmarks:action'), {
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertBookmarksAreUnmodified([bookmark1, bookmark2, bookmark3])

    def test_should_redirect_to_return_url(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        url = reverse('bookmarks:action') + '?return_url=' + reverse('bookmarks:settings.index')
        response = self.client.post(url, {
            'bulk_action': ['bulk_archive'],
            'bulk_execute': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertRedirects(response, reverse('bookmarks:settings.index'))

    def test_should_not_redirect_to_external_url(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        def post_with(return_url, follow=None):
            url = reverse('bookmarks:action') + f'?return_url={return_url}'
            return self.client.post(url, {
                'bulk_action': ['bulk_archive'],
                'bulk_execute': [''],
                'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
            }, follow=follow)

        response = post_with('https://example.com')
        self.assertRedirects(response, reverse('bookmarks:index'))
        response = post_with('//example.com')
        self.assertRedirects(response, reverse('bookmarks:index'))
        response = post_with('://example.com')
        self.assertRedirects(response, reverse('bookmarks:index'))

        response = post_with('/foo//example.com', follow=True)
        self.assertEqual(response.status_code, 404)
