from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark
from bookmarks.tests.helpers import BookmarkFactoryMixin, disable_logging


class SettingsImportViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertSuccessMessage(self, response, message: str):
        self.assertInHTML(
            f"""
            <div class="toast toast-success mb-4">{ message }</div>
        """,
            response.content.decode("utf-8"),
        )

    def assertNoSuccessMessage(self, response):
        self.assertNotContains(response, '<div class="toast toast-success mb-4">')

    def assertErrorMessage(self, response, message: str):
        self.assertInHTML(
            f"""
            <div class="toast toast-error mb-4">{ message }</div>
        """,
            response.content.decode("utf-8"),
        )

    def assertNoErrorMessage(self, response):
        self.assertNotContains(response, '<div class="toast toast-error mb-4">')

    def test_should_import_successfully(self):
        with open(
            "bookmarks/tests/resources/simple_valid_import_file.html"
        ) as import_file:
            response = self.client.post(
                reverse("bookmarks:settings.import"),
                {"import_file": import_file},
                follow=True,
            )

            self.assertRedirects(response, reverse("bookmarks:settings.general"))
            self.assertSuccessMessage(
                response, "3 bookmarks were successfully imported."
            )
            self.assertNoErrorMessage(response)

    def test_should_check_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("bookmarks:settings.import"), follow=True)

        self.assertRedirects(
            response, reverse("login") + "?next=" + reverse("bookmarks:settings.import")
        )

    def test_should_show_hint_if_there_is_no_file(self):
        response = self.client.post(reverse("bookmarks:settings.import"), follow=True)

        self.assertRedirects(response, reverse("bookmarks:settings.general"))
        self.assertNoSuccessMessage(response)
        self.assertErrorMessage(response, "Please select a file to import.")

    @disable_logging
    def test_should_show_hint_if_import_raises_exception(self):
        with open(
            "bookmarks/tests/resources/invalid_import_file.png", "rb"
        ) as import_file:
            response = self.client.post(
                reverse("bookmarks:settings.import"),
                {"import_file": import_file},
                follow=True,
            )

            self.assertRedirects(response, reverse("bookmarks:settings.general"))
            self.assertNoSuccessMessage(response)
            self.assertErrorMessage(
                response, "An error occurred during bookmark import."
            )

    @disable_logging
    def test_should_show_respective_hints_if_not_all_bookmarks_were_imported_successfully(
        self,
    ):
        with open(
            "bookmarks/tests/resources/simple_valid_import_file_with_one_invalid_bookmark.html"
        ) as import_file:
            response = self.client.post(
                reverse("bookmarks:settings.import"),
                {"import_file": import_file},
                follow=True,
            )

            self.assertRedirects(response, reverse("bookmarks:settings.general"))
            self.assertSuccessMessage(
                response, "2 bookmarks were successfully imported."
            )
            self.assertErrorMessage(
                response,
                "1 bookmarks could not be imported. Please check the logs for more details.",
            )

    def test_should_respect_map_private_flag_option(self):
        with open(
            "bookmarks/tests/resources/simple_valid_import_file.html"
        ) as import_file:
            self.client.post(
                reverse("bookmarks:settings.import"),
                {"import_file": import_file},
                follow=True,
            )

            self.assertEqual(Bookmark.objects.count(), 3)
            self.assertEqual(Bookmark.objects.all()[0].shared, False)
            self.assertEqual(Bookmark.objects.all()[1].shared, False)
            self.assertEqual(Bookmark.objects.all()[2].shared, False)

        Bookmark.objects.all().delete()

        with open(
            "bookmarks/tests/resources/simple_valid_import_file.html"
        ) as import_file:
            self.client.post(
                reverse("bookmarks:settings.import"),
                {"import_file": import_file, "map_private_flag": "on"},
                follow=True,
            )

            self.assertEqual(Bookmark.objects.count(), 3)
            self.assertEqual(Bookmark.objects.all()[0].shared, True)
            self.assertEqual(Bookmark.objects.all()[1].shared, True)
            self.assertEqual(Bookmark.objects.all()[2].shared, True)
