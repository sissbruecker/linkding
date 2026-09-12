import base64
import os

from bs4 import BeautifulSoup
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import BookmarkAsset
from bookmarks.tests.helpers import BookmarkFactoryMixin


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
        asset = self.setup_asset(
            bookmark=bookmark, file=filename, display_name=f"Snapshot {bookmark.id}"
        )
        return asset

    def setup_asset_with_uploaded_file(self, bookmark, content_type="image/png"):
        filename = f"temp_{bookmark.id}.png.gzip"
        self.setup_asset_file(filename)
        asset = self.setup_asset(
            bookmark=bookmark,
            file=filename,
            asset_type=BookmarkAsset.TYPE_UPLOAD,
            content_type=content_type,
            display_name=f"Uploaded file {bookmark.id}.png",
        )
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

    def test_snapshot_download_headers(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_file(bookmark)
        response = self.client.get(reverse("linkding:assets.view", args=[asset.id]))

        self.assertEqual(response["Content-Type"], asset.content_type)
        self.assertEqual(
            response["Content-Disposition"],
            f'inline; filename="{asset.display_name}.html"',
        )
        self.assertEqual(response["Content-Security-Policy"], "sandbox allow-scripts")

    def test_reader_view_headers(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_file(bookmark)
        response = self.client.get(reverse("linkding:assets.read", args=[asset.id]))

        self.assertEqual(response["Content-Security-Policy"], "sandbox allow-scripts")

    def test_reader_view_without_custom_css(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_file(bookmark)
        response = self.client.get(reverse("linkding:assets.read", args=[asset.id]))

        soup = BeautifulSoup(response.content, "html.parser")
        link = soup.select_one("link[rel='stylesheet'][href^='data:text/css']")
        self.assertIsNone(link)

    def test_reader_view_with_custom_css(self):
        # The reader view is sandboxed, so requests to the custom CSS view
        # would not include credentials. Custom CSS is embedded as data URL instead.
        css = "body { background-color: red; }"
        profile = self.get_or_create_test_user().profile
        profile.custom_css = css
        profile.save()

        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_file(bookmark)
        response = self.client.get(reverse("linkding:assets.read", args=[asset.id]))

        soup = BeautifulSoup(response.content, "html.parser")
        link = soup.select_one("link[rel='stylesheet'][href^='data:text/css']")
        self.assertIsNotNone(link)
        encoded = base64.b64encode(css.encode("utf-8")).decode("ascii")
        self.assertEqual(link["href"], f"data:text/css;charset=utf-8;base64,{encoded}")
        self.assertNotIn(reverse("linkding:custom_css"), response.content.decode())

    def test_reader_view_custom_css_can_not_inject_html(self):
        css = "</style><script>alert('xss')</script><style>"
        profile = self.get_or_create_test_user().profile
        profile.custom_css = css
        profile.save()

        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_file(bookmark)
        response = self.client.get(reverse("linkding:assets.read", args=[asset.id]))

        html = response.content.decode()
        self.assertNotIn("alert('xss')", html)
        self.assertNotIn("</style>", html)

    def test_uploaded_file_download_headers(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_uploaded_file(bookmark)
        response = self.client.get(reverse("linkding:assets.view", args=[asset.id]))

        self.assertEqual(response["Content-Type"], asset.content_type)
        self.assertEqual(
            response["Content-Disposition"],
            f'inline; filename="{asset.display_name}"',
        )
        self.assertEqual(response["Content-Security-Policy"], "sandbox allow-scripts")

    def test_uploaded_video_download_headers(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset_with_uploaded_file(bookmark, content_type="video/mp4")
        response = self.client.get(reverse("linkding:assets.view", args=[asset.id]))

        self.assertEqual(response["Content-Type"], asset.content_type)
        self.assertEqual(
            response["Content-Disposition"],
            f'inline; filename="{asset.display_name}"',
        )
        self.assertEqual(
            response["Content-Security-Policy"], "default-src 'none'; media-src 'self';"
        )
