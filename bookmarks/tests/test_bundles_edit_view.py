from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class BundleEditViewTestCase(TestCase, BookmarkFactoryMixin):

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

    def test_should_edit_bundle(self):
        bundle = self.setup_bundle()

        updated_data = self.create_form_data()

        response = self.client.post(
            reverse("linkding:bundles.edit", args=[bundle.id]), updated_data
        )

        self.assertRedirects(response, reverse("linkding:bundles.index"))

        bundle.refresh_from_db()
        self.assertEqual(bundle.name, updated_data["name"])
        self.assertEqual(bundle.search, updated_data["search"])
        self.assertEqual(bundle.any_tags, updated_data["any_tags"])
        self.assertEqual(bundle.all_tags, updated_data["all_tags"])
        self.assertEqual(bundle.excluded_tags, updated_data["excluded_tags"])

    def test_should_render_edit_form_with_prefilled_fields(self):
        bundle = self.setup_bundle(
            name="Test Bundle",
            search="test search terms",
            any_tags="tag1 tag2 tag3",
            all_tags="required-tag all-tag",
            excluded_tags="excluded-tag banned-tag",
        )

        response = self.client.get(reverse("linkding:bundles.edit", args=[bundle.id]))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertInHTML(
            f'<input type="text" name="name" value="{bundle.name}" '
            'autocomplete="off" placeholder=" " class="form-input" '
            'maxlength="256" required id="id_name">',
            html,
        )

        self.assertInHTML(
            f'<input type="text" name="search" value="{bundle.search}" '
            'autocomplete="off" placeholder=" " class="form-input" '
            'maxlength="256" id="id_search">',
            html,
        )

        self.assertInHTML(
            f'<input type="text" name="any_tags" value="{bundle.any_tags}" '
            'autocomplete="off" autocapitalize="off" class="form-input" '
            'maxlength="1024" id="id_any_tags">',
            html,
        )

        self.assertInHTML(
            f'<input type="text" name="all_tags" value="{bundle.all_tags}" '
            'autocomplete="off" autocapitalize="off" class="form-input" '
            'maxlength="1024" id="id_all_tags">',
            html,
        )

        self.assertInHTML(
            f'<input type="text" name="excluded_tags" value="{bundle.excluded_tags}" '
            'autocomplete="off" autocapitalize="off" class="form-input" '
            'maxlength="1024" id="id_excluded_tags">',
            html,
        )

    def test_should_return_422_with_invalid_form(self):
        bundle = self.setup_bundle(
            name="Test Bundle",
            search="test search",
            any_tags="tag1 tag2",
            all_tags="required-tag",
            excluded_tags="excluded-tag",
        )

        invalid_data = self.create_form_data({"name": ""})

        response = self.client.post(
            reverse("linkding:bundles.edit", args=[bundle.id]), invalid_data
        )

        self.assertEqual(response.status_code, 422)

    def test_should_not_allow_editing_other_users_bundles(self):
        other_user = self.setup_user(name="otheruser")
        other_users_bundle = self.setup_bundle(user=other_user)

        response = self.client.get(
            reverse("linkding:bundles.edit", args=[other_users_bundle.id])
        )
        self.assertEqual(response.status_code, 404)

        updated_data = self.create_form_data()
        response = self.client.post(
            reverse("linkding:bundles.edit", args=[other_users_bundle.id]), updated_data
        )
        self.assertEqual(response.status_code, 404)
