from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class CustomCssTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.client.force_login(self.get_or_create_test_user())

    def test_does_not_render_custom_style_tag_by_default(self):
        response = self.client.get(reverse("bookmarks:index"))
        self.assertNotContains(response, "<style>")

    def test_renders_custom_style_tag_if_user_has_custom_css(self):
        profile = self.get_or_create_test_user().profile
        profile.custom_css = "body { background-color: red; }"
        profile.save()

        response = self.client.get(reverse("bookmarks:index"))
        self.assertContains(response, "<style>body { background-color: red; }</style>")
