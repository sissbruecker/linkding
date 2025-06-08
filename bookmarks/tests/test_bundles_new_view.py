from django.test import TestCase
from django.urls import reverse

from bookmarks.models import BookmarkBundle
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BundleNewViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def create_form_data(self, overrides=None):
        if overrides is None:
            overrides = {}
        form_data = {
            "name": "Test Bundle",
            "search": "test search",
            "any_tags": "tag1 tag2",
            "all_tags": "required-tag",
            "excluded_tags": "excluded-tag",
        }
        return {**form_data, **overrides}

    def test_should_create_new_bundle(self):
        form_data = self.create_form_data()

        response = self.client.post(reverse("linkding:bundles.new"), form_data)

        self.assertEqual(BookmarkBundle.objects.count(), 1)

        bundle = BookmarkBundle.objects.first()
        self.assertEqual(bundle.owner, self.user)
        self.assertEqual(bundle.name, form_data["name"])
        self.assertEqual(bundle.search, form_data["search"])
        self.assertEqual(bundle.any_tags, form_data["any_tags"])
        self.assertEqual(bundle.all_tags, form_data["all_tags"])
        self.assertEqual(bundle.excluded_tags, form_data["excluded_tags"])

        self.assertRedirects(response, reverse("linkding:bundles.index"))

    def test_should_return_422_with_invalid_form(self):
        form_data = self.create_form_data({"name": ""})
        response = self.client.post(reverse("linkding:bundles.new"), form_data)
        self.assertEqual(response.status_code, 422)
