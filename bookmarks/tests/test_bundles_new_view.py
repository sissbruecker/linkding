from django.test import TestCase
from django.urls import reverse
from urllib.parse import urlencode

from bookmarks.models import BookmarkBundle
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class BundleNewViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):

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

    def test_should_prefill_form_from_search_query_parameters(self):
        query = "machine learning #python #ai"
        url = reverse("linkding:bundles.new") + "?" + urlencode({"q": query})
        response = self.client.get(url)

        soup = self.make_soup(response.content.decode())
        search_field = soup.select_one('input[name="search"]')
        all_tags_field = soup.select_one('input[name="all_tags"]')

        self.assertEqual(search_field.get("value"), "machine learning")
        self.assertEqual(all_tags_field.get("value"), "python ai")

    def test_should_ignore_special_search_commands(self):
        query = "python tutorial !untagged !unread"
        url = reverse("linkding:bundles.new") + "?" + urlencode({"q": query})
        response = self.client.get(url)

        soup = self.make_soup(response.content.decode())
        search_field = soup.select_one('input[name="search"]')
        all_tags_field = soup.select_one('input[name="all_tags"]')

        self.assertEqual(search_field.get("value"), "python tutorial")
        self.assertIsNone(all_tags_field.get("value"))

    def test_should_not_prefill_when_no_query_parameter(self):
        response = self.client.get(reverse("linkding:bundles.new"))

        soup = self.make_soup(response.content.decode())
        search_field = soup.select_one('input[name="search"]')
        all_tags_field = soup.select_one('input[name="all_tags"]')

        self.assertIsNone(search_field.get("value"))
        self.assertIsNone(all_tags_field.get("value"))

    def test_should_not_prefill_when_editing_existing_bundle(self):
        bundle = self.setup_bundle(
            name="Existing Bundle", search="Tutorial", all_tags="java spring"
        )

        query = "machine learning #python #ai"
        url = (
            reverse("linkding:bundles.edit", args=[bundle.id])
            + "?"
            + urlencode({"q": query})
        )
        response = self.client.get(url)

        soup = self.make_soup(response.content.decode())
        search_field = soup.select_one('input[name="search"]')
        all_tags_field = soup.select_one('input[name="all_tags"]')

        self.assertEqual(search_field.get("value"), "Tutorial")
        self.assertEqual(all_tags_field.get("value"), "java spring")

    def test_should_show_correct_preview_with_prefilled_values(self):
        bundle_tag = self.setup_tag()
        bookmark1 = self.setup_bookmark(tags=[bundle_tag])
        bookmark2 = self.setup_bookmark()
        bookmark3 = self.setup_bookmark()

        query = "#" + bundle_tag.name
        url = reverse("linkding:bundles.new") + "?" + urlencode({"q": query})
        response = self.client.get(url)

        self.assertContains(response, "Found 1 bookmarks matching this bundle")
        self.assertContains(response, bookmark1.title)
        self.assertNotContains(response, bookmark2.title)
        self.assertNotContains(response, bookmark3.title)
