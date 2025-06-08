from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class BundleIndexViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_render_bundles_list(self):
        bundles = [
            self.setup_bundle(name="Bundle 1"),
            self.setup_bundle(name="Bundle 2"),
            self.setup_bundle(name="Bundle 3"),
        ]

        response = self.client.get(reverse("linkding:bundles.index"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        for bundle in bundles:
            expected_list_item = f"""
            <div class="list-item" data-bundle-id="{bundle.id}">
                <div class="list-item-text">
                    <span class="truncate">{bundle.name}</span>
                </div>
                <div class="list-item-actions">
                    <a class="btn btn-link" href="{reverse("linkding:bundles.edit", args=[bundle.id])}">Edit</a>
                </div>
            </div>
            """

            self.assertInHTML(expected_list_item, html)

    def test_should_render_empty_state_when_no_bundles(self):
        response = self.client.get(reverse("linkding:bundles.index"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertInHTML('<p class="empty-title h5">You have no bundles yet</p>', html)
        self.assertInHTML(
            '<p class="empty-subtitle">Create your first bundle to get started</p>',
            html,
        )

    def test_should_show_add_new_bundle_button(self):
        response = self.client.get(reverse("linkding:bundles.index"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertInHTML(
            f'<a href="{reverse("linkding:bundles.new")}" class="btn btn-primary">Add new bundle</a>',
            html,
        )

    def test_should_only_show_user_bundles(self):
        user_bundle = self.setup_bundle(name="User Bundle")

        other_user = self.setup_user(name="otheruser")
        other_user_bundle = self.setup_bundle(name="Other User Bundle", user=other_user)

        response = self.client.get(reverse("linkding:bundles.index"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertInHTML(f'<span class="truncate">{user_bundle.name}</span>', html)
        self.assertNotIn(other_user_bundle.name, html)
