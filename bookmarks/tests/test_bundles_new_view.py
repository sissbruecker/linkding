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

    def test_should_increment_order_for_subsequent_bundles(self):
        # Create first bundle
        form_data_1 = self.create_form_data({"name": "Bundle 1"})
        self.client.post(reverse("linkding:bundles.new"), form_data_1)
        bundle1 = BookmarkBundle.objects.get(name="Bundle 1")
        self.assertEqual(bundle1.order, 0)

        # Create second bundle
        form_data_2 = self.create_form_data({"name": "Bundle 2"})
        self.client.post(reverse("linkding:bundles.new"), form_data_2)
        bundle2 = BookmarkBundle.objects.get(name="Bundle 2")
        self.assertEqual(bundle2.order, 1)

        # Create another bundle with a higher order
        self.setup_bundle(order=5)

        # Create third bundle
        form_data_3 = self.create_form_data({"name": "Bundle 3"})
        self.client.post(reverse("linkding:bundles.new"), form_data_3)
        bundle3 = BookmarkBundle.objects.get(name="Bundle 3")
        self.assertEqual(bundle3.order, 6)

    def test_incrementing_order_ignores_other_user_bookmark(self):
        other_user = self.setup_user()
        self.setup_bundle(user=other_user, order=10)

        form_data = self.create_form_data({"name": "Bundle 1"})
        self.client.post(reverse("linkding:bundles.new"), form_data)
        bundle1 = BookmarkBundle.objects.get(name="Bundle 1")
        self.assertEqual(bundle1.order, 0)

    def test_should_return_422_with_invalid_form(self):
        form_data = self.create_form_data({"name": ""})
        response = self.client.post(reverse("linkding:bundles.new"), form_data)
        self.assertEqual(response.status_code, 422)
