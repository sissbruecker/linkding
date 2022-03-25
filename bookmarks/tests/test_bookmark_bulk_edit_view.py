from django.contrib.auth.models import User
from django.forms import model_to_dict
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkBulkEditViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertBookmarksAreUnmodified(self, bookmarks: [Bookmark]):
        self.assertEqual(len(bookmarks), Bookmark.objects.count())

        for bookmark in bookmarks:
            self.assertEqual(model_to_dict(bookmark), model_to_dict(Bookmark.objects.get(id=bookmark.id)))

    def test_bulk_archive(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_archive': [''],
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

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_archive': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertFalse(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertFalse(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_bulk_unarchive(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        bookmark3 = self.setup_bookmark(is_archived=True)

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_unarchive': [''],
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

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_unarchive': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertTrue(Bookmark.objects.get(id=bookmark1.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark2.id).is_archived)
        self.assertTrue(Bookmark.objects.get(id=bookmark3.id).is_archived)

    def test_bulk_delete(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_delete': [''],
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

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_delete': [''],
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

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_tag': [''],
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

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_tag': [''],
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

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_untag': [''],
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

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_untag': [''],
            'bulk_tag_string': [f'{tag1.name} {tag2.name}'],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        bookmark3.refresh_from_db()

        self.assertCountEqual(bookmark1.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark2.tags.all(), [tag1, tag2])
        self.assertCountEqual(bookmark3.tags.all(), [tag1, tag2])

    def test_bulk_edit_handles_empty_bookmark_id(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        response = self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_archive': [''],
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.post(reverse('bookmarks:bulk_edit'), {
            'bulk_archive': [''],
            'bookmark_id': [],
        })
        self.assertEqual(response.status_code, 302)

        self.assertBookmarksAreUnmodified([bookmark1, bookmark2, bookmark3])

    def test_empty_action_does_not_modify_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        self.client.post(reverse('bookmarks:bulk_edit'), {
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertBookmarksAreUnmodified([bookmark1, bookmark2, bookmark3])

    def test_bulk_edit_should_redirect_to_return_url(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        url = reverse('bookmarks:bulk_edit') + '?return_url=' + reverse('bookmarks:settings.index')
        response = self.client.post(url, {
            'bulk_archive': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertRedirects(response, reverse('bookmarks:settings.index'))

    def test_bulk_edit_should_not_redirect_to_external_url(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        url = reverse('bookmarks:bulk_edit') + '?return_url=https://example.com'
        response = self.client.post(url, {
            'bulk_archive': [''],
            'bookmark_id': [str(bookmark1.id), str(bookmark2.id), str(bookmark3.id)],
        })

        self.assertRedirects(response, reverse('bookmarks:index'))
