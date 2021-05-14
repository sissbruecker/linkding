from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class SettingsImportViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertFormSuccessHint(self, response, text: str):
        self.assertContains(response, '<div class="has-success">')
        self.assertContains(response, text)

    def assertNoFormSuccessHint(self, response):
        self.assertNotContains(response, '<div class="has-success">')

    def assertFormErrorHint(self, response, text: str):
        self.assertContains(response, '<div class="has-error">')
        self.assertContains(response, text)

    def assertNoFormErrorHint(self, response):
        self.assertNotContains(response, '<div class="has-error">')

    def test_should_import_successfully(self):
        with open('bookmarks/tests/resources/simple_valid_import_file.html') as import_file:
            response = self.client.post(
                reverse('bookmarks:settings.import'),
                {'import_file': import_file},
                follow=True
            )

            self.assertRedirects(response, reverse('bookmarks:settings.general'))
            self.assertFormSuccessHint(response, '3 bookmarks were successfully imported')
            self.assertNoFormErrorHint(response)

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('bookmarks:settings.import'), follow=True)

        self.assertRedirects(response, reverse('login') + '?next=' + reverse('bookmarks:settings.import'))

    def test_should_show_hint_if_there_is_no_file(self):
        response = self.client.post(
            reverse('bookmarks:settings.import'),
            follow=True
        )

        self.assertRedirects(response, reverse('bookmarks:settings.general'))
        self.assertNoFormSuccessHint(response)
        self.assertFormErrorHint(response, 'Please select a file to import.')

    def test_should_show_hint_if_import_raises_exception(self):
        with open('bookmarks/tests/resources/invalid_import_file.png', 'rb') as import_file:
            response = self.client.post(
                reverse('bookmarks:settings.import'),
                {'import_file': import_file},
                follow=True
            )

            self.assertRedirects(response, reverse('bookmarks:settings.general'))
            self.assertNoFormSuccessHint(response)
            self.assertFormErrorHint(response, 'An error occurred during bookmark import.')

    def test_should_show_respective_hints_if_not_all_bookmarks_were_imported_successfully(self):
        with open('bookmarks/tests/resources/simple_valid_import_file_with_one_invalid_bookmark.html') as import_file:
            response = self.client.post(
                reverse('bookmarks:settings.import'),
                {'import_file': import_file},
                follow=True
            )

            self.assertRedirects(response, reverse('bookmarks:settings.general'))
            self.assertFormSuccessHint(response, '2 bookmarks were successfully imported')
            self.assertFormErrorHint(response, '1 bookmarks could not be imported')
