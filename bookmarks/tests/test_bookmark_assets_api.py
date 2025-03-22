import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from bookmarks.models import BookmarkAsset
from bookmarks.tests.helpers import LinkdingApiTestCase, BookmarkFactoryMixin


class BookmarkAssetsApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.setup_temp_assets_dir()

    def assertAsset(self, asset: BookmarkAsset, data: dict):
        self.assertEqual(asset.id, data["id"])
        self.assertEqual(asset.bookmark.id, data["bookmark"])
        self.assertEqual(
            asset.date_created.isoformat().replace("+00:00", "Z"), data["date_created"]
        )
        self.assertEqual(asset.file_size, data["file_size"])
        self.assertEqual(asset.asset_type, data["asset_type"])
        self.assertEqual(asset.content_type, data["content_type"])
        self.assertEqual(asset.display_name, data["display_name"])
        self.assertEqual(asset.status, data["status"])

    def test_asset_list(self):
        self.authenticate()

        bookmark1 = self.setup_bookmark(url="https://example1.com")
        bookmark1_assets = [
            self.setup_asset(bookmark=bookmark1),
            self.setup_asset(bookmark=bookmark1),
            self.setup_asset(bookmark=bookmark1),
        ]

        bookmark2 = self.setup_bookmark(url="https://example2.com")
        bookmark2_assets = [
            self.setup_asset(bookmark=bookmark2),
            self.setup_asset(bookmark=bookmark2),
            self.setup_asset(bookmark=bookmark2),
        ]

        url = reverse(
            "linkding:bookmark_asset-list", kwargs={"bookmark_id": bookmark1.id}
        )
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertAsset(bookmark1_assets[0], response.data["results"][0])
        self.assertAsset(bookmark1_assets[1], response.data["results"][1])
        self.assertAsset(bookmark1_assets[2], response.data["results"][2])

        url = reverse(
            "linkding:bookmark_asset-list", kwargs={"bookmark_id": bookmark2.id}
        )
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertAsset(bookmark2_assets[0], response.data["results"][0])
        self.assertAsset(bookmark2_assets[1], response.data["results"][1])
        self.assertAsset(bookmark2_assets[2], response.data["results"][2])

    def test_asset_list_only_returns_assets_for_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        self.setup_asset(bookmark=bookmark)

        url = reverse(
            "linkding:bookmark_asset-list", kwargs={"bookmark_id": bookmark.id}
        )
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_asset_list_requires_authentication(self):
        bookmark = self.setup_bookmark()
        url = reverse(
            "linkding:bookmark_asset-list", kwargs={"bookmark_id": bookmark.id}
        )
        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

    def test_asset_detail(self):
        self.authenticate()

        bookmark = self.setup_bookmark()
        asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_UPLOAD,
            file="cats.png",
            file_size=1234,
            content_type="image/png",
            display_name="cats.png",
            status=BookmarkAsset.STATUS_PENDING,
            gzip=False,
        )
        url = reverse(
            "linkding:bookmark_asset-detail",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertAsset(asset, response.data)

    def test_asset_detail_only_returns_asset_for_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        asset = self.setup_asset(bookmark=bookmark)

        url = reverse(
            "linkding:bookmark_asset-detail",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_asset_detail_requires_authentication(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(bookmark=bookmark)
        url = reverse(
            "linkding:bookmark_asset-detail",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

    def test_asset_download_with_snapshot_asset(self):
        self.authenticate()

        file_content = """
            <html>
            <head>
                <title>Test</title>
            </head>
            <body>
                <h1>Test</h1>
            </body>
        """
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            display_name="Snapshot from today",
            content_type="text/html",
            gzip=True,
        )
        self.setup_asset_file(asset=asset, file_content=file_content)

        url = reverse(
            "linkding:bookmark_asset-download",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        response = self.get(url, expected_status_code=status.HTTP_200_OK)

        self.assertEqual(response["Content-Type"], "text/html")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="Snapshot from today.html"',
        )
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertEqual(content, file_content)

    def test_asset_download_with_uploaded_asset(self):
        self.authenticate()

        file_content = "some file content"
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_UPLOAD,
            display_name="cats.png",
            content_type="image/png",
            gzip=False,
        )
        self.setup_asset_file(asset=asset, file_content=file_content)

        url = reverse(
            "linkding:bookmark_asset-download",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        response = self.get(url, expected_status_code=status.HTTP_200_OK)

        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="cats.png"',
        )
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertEqual(content, file_content)

    def test_asset_download_with_missing_file(self):
        self.authenticate()

        bookmark = self.setup_bookmark()
        asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_UPLOAD,
            display_name="cats.png",
            content_type="image/png",
            gzip=False,
        )

        url = reverse(
            "linkding:bookmark_asset-download",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_asset_download_only_returns_asset_for_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        asset = self.setup_asset(bookmark=bookmark)

        url = reverse(
            "linkding:bookmark_asset-download",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_asset_download_requires_authentication(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(bookmark=bookmark)
        url = reverse(
            "linkding:bookmark_asset-download",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

    def create_upload_body(self):
        url = "https://example.com"
        file_content = b"dummy content"
        file = io.BytesIO(file_content)
        file.name = "snapshot.html"

        return {"url": url, "file": file}

    def test_upload_asset(self):
        self.authenticate()

        bookmark = self.setup_bookmark()
        url = reverse(
            "linkding:bookmark_asset-upload", kwargs={"bookmark_id": bookmark.id}
        )
        file_content = b"test file content"
        file_name = "test.txt"
        file = SimpleUploadedFile(file_name, file_content, content_type="text/plain")

        response = self.client.post(url, {"file": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        asset = BookmarkAsset.objects.get(id=response.data["id"])
        self.assertEqual(asset.bookmark, bookmark)
        self.assertEqual(asset.display_name, file_name)
        self.assertEqual(asset.asset_type, BookmarkAsset.TYPE_UPLOAD)
        self.assertEqual(asset.content_type, "text/plain")
        self.assertEqual(asset.file_size, len(file_content))
        self.assertFalse(asset.gzip)

        content = self.read_asset_file(asset)
        self.assertEqual(content, file_content)

    def test_upload_asset_with_missing_file(self):
        self.authenticate()

        bookmark = self.setup_bookmark()
        url = reverse(
            "linkding:bookmark_asset-upload", kwargs={"bookmark_id": bookmark.id}
        )

        response = self.client.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_asset_only_works_for_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        url = reverse(
            "linkding:bookmark_asset-upload", kwargs={"bookmark_id": bookmark.id}
        )

        response = self.client.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_asset_requires_authentication(self):
        bookmark = self.setup_bookmark()
        url = reverse(
            "linkding:bookmark_asset-upload", kwargs={"bookmark_id": bookmark.id}
        )

        response = self.client.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(LD_DISABLE_ASSET_UPLOAD=True)
    def test_upload_asset_disabled(self):
        self.authenticate()
        bookmark = self.setup_bookmark()
        url = reverse(
            "linkding:bookmark_asset-upload", kwargs={"bookmark_id": bookmark.id}
        )
        response = self.client.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_asset(self):
        self.authenticate()

        bookmark = self.setup_bookmark()
        asset = self.setup_asset(bookmark=bookmark)
        self.setup_asset_file(asset=asset)

        url = reverse(
            "linkding:bookmark_asset-detail",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)

        self.assertFalse(BookmarkAsset.objects.filter(id=asset.id).exists())
        self.assertFalse(self.has_asset_file(asset))

    def test_delete_asset_only_works_for_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        asset = self.setup_asset(bookmark=bookmark)

        url = reverse(
            "linkding:bookmark_asset-detail",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        self.delete(url, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_delete_asset_requires_authentication(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(bookmark=bookmark)
        url = reverse(
            "linkding:bookmark_asset-detail",
            kwargs={"bookmark_id": asset.bookmark.id, "pk": asset.id},
        )
        self.delete(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)
