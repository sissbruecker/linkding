from django.test import TestCase
from django.urls import reverse

from bookmarks.models import BookmarkBundle
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BundleIndexViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_render_bundle_list(self):
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
                    <button ld-confirm-button type="submit" name="remove_bundle" value="{bundle.id}" class="btn btn-link">Remove</button>
                </div>
            </div>
            """

            self.assertInHTML(expected_list_item, html)

    def test_renders_user_owned_bundles_only(self):
        user_bundle = self.setup_bundle(name="User Bundle")

        other_user = self.setup_user(name="otheruser")
        other_user_bundle = self.setup_bundle(name="Other User Bundle", user=other_user)

        response = self.client.get(reverse("linkding:bundles.index"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertInHTML(f'<span class="truncate">{user_bundle.name}</span>', html)
        self.assertNotIn(other_user_bundle.name, html)

    def test_empty_state(self):
        response = self.client.get(reverse("linkding:bundles.index"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertInHTML('<p class="empty-title h5">You have no bundles yet</p>', html)
        self.assertInHTML(
            '<p class="empty-subtitle">Create your first bundle to get started</p>',
            html,
        )

    def test_add_new_button(self):
        response = self.client.get(reverse("linkding:bundles.index"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertInHTML(
            f'<a href="{reverse("linkding:bundles.new")}" class="btn btn-primary">Add new bundle</a>',
            html,
        )

    def test_remove_bundle(self):
        bundle = self.setup_bundle(name="Test Bundle")

        response = self.client.post(
            reverse("linkding:bundles.index"),
            {"remove_bundle": str(bundle.id)},
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("linkding:bundles.index"))

        self.assertFalse(BookmarkBundle.objects.filter(id=bundle.id).exists())

    def test_remove_other_user_bundle(self):
        other_user = self.setup_user(name="otheruser")
        other_user_bundle = self.setup_bundle(name="Other User Bundle", user=other_user)

        response = self.client.post(
            reverse("linkding:bundles.index"),
            {"remove_bundle": str(other_user_bundle.id)},
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(BookmarkBundle.objects.filter(id=other_user_bundle.id).exists())

    def test_remove_non_existing_bundle(self):
        non_existent_id = 99999

        response = self.client.post(
            reverse("linkding:bundles.index"),
            {"remove_bundle": str(non_existent_id)},
        )

        self.assertEqual(response.status_code, 404)

    def test_post_without_action(self):
        bundle = self.setup_bundle(name="Test Bundle")

        response = self.client.post(reverse("linkding:bundles.index"), {})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(BookmarkBundle.objects.filter(id=bundle.id).exists())
