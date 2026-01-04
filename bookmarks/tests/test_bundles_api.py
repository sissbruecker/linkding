from django.urls import reverse
from rest_framework import status

from bookmarks.models import BookmarkBundle
from bookmarks.tests.helpers import BookmarkFactoryMixin, LinkdingApiTestCase


class BundlesApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    def assertBundle(self, bundle: BookmarkBundle, data: dict):
        self.assertEqual(bundle.id, data["id"])
        self.assertEqual(bundle.name, data["name"])
        self.assertEqual(bundle.search, data["search"])
        self.assertEqual(bundle.any_tags, data["any_tags"])
        self.assertEqual(bundle.all_tags, data["all_tags"])
        self.assertEqual(bundle.excluded_tags, data["excluded_tags"])
        self.assertEqual(bundle.order, data["order"])
        self.assertEqual(
            bundle.date_created.isoformat().replace("+00:00", "Z"), data["date_created"]
        )
        self.assertEqual(
            bundle.date_modified.isoformat().replace("+00:00", "Z"),
            data["date_modified"],
        )

    def test_bundle_list(self):
        self.authenticate()

        bundles = [
            self.setup_bundle(name="Bundle 1", order=0),
            self.setup_bundle(name="Bundle 2", order=1),
            self.setup_bundle(name="Bundle 3", order=2),
        ]

        url = reverse("linkding:bundle-list")
        response = self.get(url, expected_status_code=status.HTTP_200_OK)

        self.assertEqual(len(response.data["results"]), 3)
        self.assertBundle(bundles[0], response.data["results"][0])
        self.assertBundle(bundles[1], response.data["results"][1])
        self.assertBundle(bundles[2], response.data["results"][2])

    def test_bundle_list_only_returns_own_bundles(self):
        self.authenticate()

        user_bundles = [
            self.setup_bundle(name="User Bundle 1"),
            self.setup_bundle(name="User Bundle 2"),
        ]

        other_user = self.setup_user()
        self.setup_bundle(name="Other User Bundle 1", user=other_user)
        self.setup_bundle(name="Other User Bundle 2", user=other_user)

        url = reverse("linkding:bundle-list")
        response = self.get(url, expected_status_code=status.HTTP_200_OK)

        self.assertEqual(len(response.data["results"]), 2)
        self.assertBundle(user_bundles[0], response.data["results"][0])
        self.assertBundle(user_bundles[1], response.data["results"][1])

    def test_bundle_list_requires_authentication(self):
        url = reverse("linkding:bundle-list")
        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

    def test_bundle_detail(self):
        self.authenticate()

        bundle = self.setup_bundle(
            name="Test Bundle",
            search="test search",
            any_tags="tag1 tag2",
            all_tags="required-tag",
            excluded_tags="excluded-tag",
            order=5,
        )

        url = reverse("linkding:bundle-detail", kwargs={"pk": bundle.id})
        response = self.get(url, expected_status_code=status.HTTP_200_OK)

        self.assertBundle(bundle, response.data)

    def test_bundle_detail_only_returns_own_bundles(self):
        self.authenticate()

        other_user = self.setup_user()
        other_bundle = self.setup_bundle(name="Other User Bundle", user=other_user)

        url = reverse("linkding:bundle-detail", kwargs={"pk": other_bundle.id})
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_bundle_detail_requires_authentication(self):
        bundle = self.setup_bundle()
        url = reverse("linkding:bundle-detail", kwargs={"pk": bundle.id})
        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

    def test_create_bundle(self):
        self.authenticate()

        bundle_data = {
            "name": "New Bundle",
            "search": "test search",
            "any_tags": "tag1 tag2",
            "all_tags": "required-tag",
            "excluded_tags": "excluded-tag",
        }

        url = reverse("linkding:bundle-list")
        response = self.post(
            url, bundle_data, expected_status_code=status.HTTP_201_CREATED
        )

        bundle = BookmarkBundle.objects.get(id=response.data["id"])
        self.assertEqual(bundle.name, bundle_data["name"])
        self.assertEqual(bundle.search, bundle_data["search"])
        self.assertEqual(bundle.any_tags, bundle_data["any_tags"])
        self.assertEqual(bundle.all_tags, bundle_data["all_tags"])
        self.assertEqual(bundle.excluded_tags, bundle_data["excluded_tags"])
        self.assertEqual(bundle.owner, self.user)
        self.assertEqual(bundle.order, 0)

        self.assertBundle(bundle, response.data)

    def test_create_bundle_auto_increments_order(self):
        self.authenticate()

        self.setup_bundle(name="Existing Bundle", order=2)

        bundle_data = {"name": "New Bundle", "search": "test search"}

        url = reverse("linkding:bundle-list")
        response = self.post(
            url, bundle_data, expected_status_code=status.HTTP_201_CREATED
        )

        bundle = BookmarkBundle.objects.get(id=response.data["id"])
        self.assertEqual(bundle.order, 3)

    def test_create_bundle_with_custom_order(self):
        self.authenticate()

        bundle_data = {"name": "New Bundle", "order": 10}

        url = reverse("linkding:bundle-list")
        response = self.post(
            url, bundle_data, expected_status_code=status.HTTP_201_CREATED
        )

        bundle = BookmarkBundle.objects.get(id=response.data["id"])
        self.assertEqual(bundle.order, 10)

    def test_create_bundle_requires_name(self):
        self.authenticate()

        bundle_data = {"search": "test search"}

        url = reverse("linkding:bundle-list")
        self.post(url, bundle_data, expected_status_code=status.HTTP_400_BAD_REQUEST)

    def test_create_bundle_fields_can_be_empty(self):
        self.authenticate()

        bundle_data = {
            "name": "Minimal Bundle",
            "search": "",
            "any_tags": "",
            "all_tags": "",
            "excluded_tags": "",
        }

        url = reverse("linkding:bundle-list")
        response = self.post(
            url, bundle_data, expected_status_code=status.HTTP_201_CREATED
        )

        bundle = BookmarkBundle.objects.get(id=response.data["id"])
        self.assertEqual(bundle.name, "Minimal Bundle")
        self.assertEqual(bundle.search, "")
        self.assertEqual(bundle.any_tags, "")
        self.assertEqual(bundle.all_tags, "")
        self.assertEqual(bundle.excluded_tags, "")

    def test_create_bundle_requires_authentication(self):
        bundle_data = {"name": "New Bundle"}

        url = reverse("linkding:bundle-list")
        self.post(url, bundle_data, expected_status_code=status.HTTP_401_UNAUTHORIZED)

    def test_update_bundle_put(self):
        self.authenticate()

        bundle = self.setup_bundle(
            name="Original Bundle",
            search="original search",
            any_tags="original-tag",
            order=1,
        )

        updated_data = {
            "name": "Updated Bundle",
            "search": "updated search",
            "any_tags": "updated-tag1 updated-tag2",
            "all_tags": "required-updated-tag",
            "excluded_tags": "excluded-updated-tag",
            "order": 5,
        }

        url = reverse("linkding:bundle-detail", kwargs={"pk": bundle.id})
        response = self.put(url, updated_data, expected_status_code=status.HTTP_200_OK)

        bundle.refresh_from_db()
        self.assertEqual(bundle.name, updated_data["name"])
        self.assertEqual(bundle.search, updated_data["search"])
        self.assertEqual(bundle.any_tags, updated_data["any_tags"])
        self.assertEqual(bundle.all_tags, updated_data["all_tags"])
        self.assertEqual(bundle.excluded_tags, updated_data["excluded_tags"])
        self.assertEqual(bundle.order, updated_data["order"])

        self.assertBundle(bundle, response.data)

    def test_update_bundle_patch(self):
        self.authenticate()

        bundle = self.setup_bundle(
            name="Original Bundle", search="original search", any_tags="original-tag"
        )

        updated_data = {
            "name": "Partially Updated Bundle",
            "search": "partially updated search",
        }

        url = reverse("linkding:bundle-detail", kwargs={"pk": bundle.id})
        response = self.patch(
            url, updated_data, expected_status_code=status.HTTP_200_OK
        )

        bundle.refresh_from_db()
        self.assertEqual(bundle.name, updated_data["name"])
        self.assertEqual(bundle.search, updated_data["search"])
        self.assertEqual(bundle.any_tags, "original-tag")  # Should remain unchanged

        self.assertBundle(bundle, response.data)

    def test_update_bundle_only_allows_own_bundles(self):
        self.authenticate()

        other_user = self.setup_user()
        other_bundle = self.setup_bundle(name="Other User Bundle", user=other_user)

        updated_data = {"name": "Updated Bundle"}

        url = reverse("linkding:bundle-detail", kwargs={"pk": other_bundle.id})
        self.put(url, updated_data, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_update_bundle_requires_authentication(self):
        bundle = self.setup_bundle()
        updated_data = {"name": "Updated Bundle"}

        url = reverse("linkding:bundle-detail", kwargs={"pk": bundle.id})
        self.put(url, updated_data, expected_status_code=status.HTTP_401_UNAUTHORIZED)

    def test_delete_bundle(self):
        self.authenticate()

        bundle = self.setup_bundle(name="Bundle to Delete")

        url = reverse("linkding:bundle-detail", kwargs={"pk": bundle.id})
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)

        self.assertFalse(BookmarkBundle.objects.filter(id=bundle.id).exists())

    def test_delete_bundle_updates_order(self):
        self.authenticate()

        bundle1 = self.setup_bundle(name="Bundle 1", order=0)
        bundle2 = self.setup_bundle(name="Bundle 2", order=1)
        bundle3 = self.setup_bundle(name="Bundle 3", order=2)

        url = reverse("linkding:bundle-detail", kwargs={"pk": bundle2.id})
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)

        self.assertFalse(BookmarkBundle.objects.filter(id=bundle2.id).exists())

        # Check that the remaining bundles have updated orders
        bundle1.refresh_from_db()
        bundle3.refresh_from_db()
        self.assertEqual(bundle1.order, 0)
        self.assertEqual(bundle3.order, 1)

    def test_delete_bundle_only_allows_own_bundles(self):
        self.authenticate()

        other_user = self.setup_user()
        other_bundle = self.setup_bundle(name="Other User Bundle", user=other_user)

        url = reverse("linkding:bundle-detail", kwargs={"pk": other_bundle.id})
        self.delete(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        self.assertTrue(BookmarkBundle.objects.filter(id=other_bundle.id).exists())

    def test_delete_bundle_requires_authentication(self):
        bundle = self.setup_bundle()
        url = reverse("linkding:bundle-detail", kwargs={"pk": bundle.id})
        self.delete(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.assertTrue(BookmarkBundle.objects.filter(id=bundle.id).exists())

    def test_bundles_ordered_by_order_field(self):
        self.authenticate()

        self.setup_bundle(name="Third Bundle", order=2)
        self.setup_bundle(name="First Bundle", order=0)
        self.setup_bundle(name="Second Bundle", order=1)

        url = reverse("linkding:bundle-list")
        response = self.get(url, expected_status_code=status.HTTP_200_OK)

        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["name"], "First Bundle")
        self.assertEqual(response.data["results"][1]["name"], "Second Bundle")
        self.assertEqual(response.data["results"][2]["name"], "Third Bundle")
