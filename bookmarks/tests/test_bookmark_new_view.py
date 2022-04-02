from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkNewViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def create_form_data(self, overrides=None):
        if overrides is None:
            overrides = {}
        form_data = {
            'url': 'http://example.com',
            'tag_string': 'tag1 tag2',
            'title': 'test title',
            'description': 'test description',
            'auto_close': '',
        }
        return {**form_data, **overrides}

    def test_should_create_new_bookmark(self):
        form_data = self.create_form_data()

        self.client.post(reverse('bookmarks:new'), form_data)

        self.assertEqual(Bookmark.objects.count(), 1)

        bookmark = Bookmark.objects.first()
        self.assertEqual(bookmark.owner, self.user)
        self.assertEqual(bookmark.url, form_data['url'])
        self.assertEqual(bookmark.title, form_data['title'])
        self.assertEqual(bookmark.description, form_data['description'])
        self.assertEqual(bookmark.tags.count(), 2)
        self.assertEqual(bookmark.tags.all()[0].name, 'tag1')
        self.assertEqual(bookmark.tags.all()[1].name, 'tag2')

    def test_should_prefill_url_from_url_parameter(self):
        response = self.client.get(reverse('bookmarks:new') + '?url=http://example.com')
        html = response.content.decode()

        self.assertInHTML(
            '<input type="text" name="url" value="http://example.com" '
            'placeholder=" " autofocus class="form-input" required '
            'id="id_url">',
            html)

    def test_should_enable_auto_close_when_specified_in_url_parameter(self):
        response = self.client.get(
            reverse('bookmarks:new') + '?auto_close')
        html = response.content.decode()

        self.assertInHTML(
            '<input type="hidden" name="auto_close" value="true" '
            'id="id_auto_close">',
            html)

    def test_should_not_enable_auto_close_when_not_specified_in_url_parameter(
            self):
        response = self.client.get(reverse('bookmarks:new'))
        html = response.content.decode()

        self.assertInHTML('<input type="hidden" name="auto_close" id="id_auto_close">',html)

    def test_should_redirect_to_index_view(self):
        form_data = self.create_form_data()

        response = self.client.post(reverse('bookmarks:new'), form_data)

        self.assertRedirects(response, reverse('bookmarks:index'))

    def test_should_not_redirect_to_external_url(self):
        form_data = self.create_form_data()

        response = self.client.post(reverse('bookmarks:new') + '?return_url=https://example.com', form_data)

        self.assertRedirects(response, reverse('bookmarks:index'))

    def test_auto_close_should_redirect_to_close_view(self):
        form_data = self.create_form_data({'auto_close': 'true'})

        response = self.client.post(reverse('bookmarks:new'), form_data)

        self.assertRedirects(response, reverse('bookmarks:close'))
