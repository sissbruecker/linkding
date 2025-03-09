import os

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import (
    BookmarkFactoryMixin,
)


class BookmarkAssetViewTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self) -> None:
        self.setup_temp_assets_dir()
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def setup_asset_file(self, filename):
        filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
        with open(filepath, "w") as f:
            f.write("test")

    def setup_asset_with_file(self, bookmark):
        filename = f"temp_{bookmark.id}.html.gzip"
        self.setup_asset_file(filename)
        asset = self.setup_asset(bookmark=bookmark, file=filename)
        return asset

    def view_access_test(self, view_name: str):
        # own bookmark
        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 200)

        # other user's bookmark
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 404)

        # shared, sharing disabled
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 404)

        # unshared, sharing enabled
        profile = other_user.profile
        profile.enable_sharing = True
        profile.save()
        bookmark = self.setup_bookmark(user=other_user, shared=False)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 404)

        # shared, sharing enabled
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 200)

    def view_access_guest_user_test(self, view_name: str):
        self.client.logout()

        # unshared, sharing disabled
        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 404)

        # shared, sharing disabled
        bookmark = self.setup_bookmark(shared=True)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 404)

        # unshared, sharing enabled
        profile = self.get_or_create_test_user().profile
        profile.enable_sharing = True
        profile.save()
        bookmark = self.setup_bookmark(shared=False)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 404)

        # shared, sharing enabled
        bookmark = self.setup_bookmark(shared=True)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 404)

        # unshared, public sharing enabled
        profile.enable_public_sharing = True
        profile.save()
        bookmark = self.setup_bookmark(shared=False)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 404)

        # shared, public sharing enabled
        bookmark = self.setup_bookmark(shared=True)
        asset = self.setup_asset_with_file(bookmark)

        response = self.client.get(reverse(view_name, args=[asset.id]))
        self.assertEqual(response.status_code, 200)

    def test_view_access(self):
        self.view_access_test("linkding:assets.view")

    def test_view_access_guest_user(self):
        self.view_access_guest_user_test("linkding:assets.view")

    def test_reader_view_access(self):
        self.view_access_test("linkding:assets.read")

    def test_reader_view_access_guest_user(self):
        self.view_access_guest_user_test("linkding:assets.read")
