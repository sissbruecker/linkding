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
            <div class="list-item" data-bundle-id="{bundle.id}" draggable="true">
              <div class="list-item-icon text-secondary">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                  <path d="M9 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>
                  <path d="M9 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>
                  <path d="M9 19m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>
                  <path d="M15 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>
                  <path d="M15 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>
                  <path d="M15 19m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>
                </svg>
              </div>
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
            reverse("linkding:bundles.action"),
            {"remove_bundle": str(bundle.id)},
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("linkding:bundles.index"))

        self.assertFalse(BookmarkBundle.objects.filter(id=bundle.id).exists())

    def test_remove_other_user_bundle(self):
        other_user = self.setup_user(name="otheruser")
        other_user_bundle = self.setup_bundle(name="Other User Bundle", user=other_user)

        response = self.client.post(
            reverse("linkding:bundles.action"),
            {"remove_bundle": str(other_user_bundle.id)},
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(BookmarkBundle.objects.filter(id=other_user_bundle.id).exists())

    def assertBundleOrder(self, expected_bundles, user=None):
        if user is None:
            user = self.user
        actual_bundles = BookmarkBundle.objects.filter(owner=user).order_by("order")
        self.assertEqual(len(actual_bundles), len(expected_bundles))
        for i, bundle in enumerate(expected_bundles):
            self.assertEqual(actual_bundles[i].id, bundle.id)
            self.assertEqual(actual_bundles[i].order, i)

    def move_bundle(self, bundle: BookmarkBundle, position: int):
        return self.client.post(
            reverse("linkding:bundles.action"),
            {"move_bundle": str(bundle.id), "move_position": position},
        )

    def test_move_bundle(self):
        bundle1 = self.setup_bundle(name="Bundle 1", order=0)
        bundle2 = self.setup_bundle(name="Bundle 2", order=1)
        bundle3 = self.setup_bundle(name="Bundle 3", order=2)

        self.move_bundle(bundle1, 1)
        self.assertBundleOrder([bundle2, bundle1, bundle3])

        self.move_bundle(bundle1, 0)
        self.assertBundleOrder([bundle1, bundle2, bundle3])

        self.move_bundle(bundle1, 2)
        self.assertBundleOrder([bundle2, bundle3, bundle1])

        self.move_bundle(bundle1, 2)
        self.assertBundleOrder([bundle2, bundle3, bundle1])

    def test_move_bundle_response(self):
        bundle1 = self.setup_bundle(name="Bundle 1", order=0)
        self.setup_bundle(name="Bundle 2", order=1)

        response = self.move_bundle(bundle1, 1)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("linkding:bundles.index"))

    def test_can_only_move_user_owned_bundles(self):
        other_user = self.setup_user()
        other_user_bundle1 = self.setup_bundle(user=other_user)
        self.setup_bundle(user=other_user)

        response = self.move_bundle(other_user_bundle1, 1)
        self.assertEqual(response.status_code, 404)

    def test_move_bundle_only_affects_own_bundles(self):
        user_bundle1 = self.setup_bundle(name="User Bundle 1", order=0)
        user_bundle2 = self.setup_bundle(name="User Bundle 2", order=1)

        other_user = self.setup_user(name="otheruser")
        other_user_bundle = self.setup_bundle(
            name="Other User Bundle", user=other_user, order=0
        )

        # Move user bundle
        self.move_bundle(user_bundle1, 1)
        self.assertBundleOrder([user_bundle2, user_bundle1], user=self.user)

        # Check that other user's bundle is unaffected
        self.assertBundleOrder([other_user_bundle], user=other_user)

    def test_remove_non_existing_bundle(self):
        non_existent_id = 99999

        response = self.client.post(
            reverse("linkding:bundles.action"),
            {"remove_bundle": str(non_existent_id)},
        )

        self.assertEqual(response.status_code, 404)

    def test_post_without_action(self):
        bundle = self.setup_bundle(name="Test Bundle")

        response = self.client.post(reverse("linkding:bundles.action"), {})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("linkding:bundles.index"))

        self.assertTrue(BookmarkBundle.objects.filter(id=bundle.id).exists())
