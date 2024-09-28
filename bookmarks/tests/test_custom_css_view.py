from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class CustomCssViewTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_with_empty_css(self):
        response = self.client.get(reverse("bookmarks:custom_css"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/css")
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=2592000")
        self.assertEqual(response.content.decode(), "")

    def test_with_custom_css(self):
        css = "body { background-color: red; }"
        self.user.profile.custom_css = css
        self.user.profile.save()

        response = self.client.get(reverse("bookmarks:custom_css"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/css")
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=2592000")
        self.assertEqual(response.content.decode(), css)
