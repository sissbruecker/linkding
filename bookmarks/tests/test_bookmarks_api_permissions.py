import urllib.parse

from django.urls import reverse
from rest_framework import status

from bookmarks.tests.helpers import BookmarkFactoryMixin, LinkdingApiTestCase


class BookmarksApiPermissionsTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    def authenticate(self) -> None:
        self.api_token = self.setup_api_token()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.api_token.key)

    def test_list_bookmarks_requires_authentication(self):
        self.get(
            reverse("linkding:bookmark-list"),
            expected_status_code=status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate()
        self.get(
            reverse("linkding:bookmark-list"), expected_status_code=status.HTTP_200_OK
        )

    def test_list_archived_bookmarks_requires_authentication(self):
        self.get(
            reverse("linkding:bookmark-archived"),
            expected_status_code=status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate()
        self.get(
            reverse("linkding:bookmark-archived"),
            expected_status_code=status.HTTP_200_OK,
        )

    def test_list_shared_bookmarks_does_not_require_authentication(self):
        self.get(
            reverse("linkding:bookmark-shared"),
            expected_status_code=status.HTTP_200_OK,
        )

        self.authenticate()
        self.get(
            reverse("linkding:bookmark-shared"),
            expected_status_code=status.HTTP_200_OK,
        )

    def test_create_bookmark_requires_authentication(self):
        data = {
            "url": "https://example.com/",
            "title": "Test title",
            "description": "Test description",
            "notes": "Test notes",
            "is_archived": False,
            "unread": False,
            "shared": False,
            "tag_names": ["tag1", "tag2"],
        }

        self.post(reverse("linkding:bookmark-list"), data, status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.post(reverse("linkding:bookmark-list"), data, status.HTTP_201_CREATED)

    def test_get_bookmark_requires_authentication(self):
        bookmark = self.setup_bookmark()
        url = reverse("linkding:bookmark-detail", args=[bookmark.id])

        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.get(url, expected_status_code=status.HTTP_200_OK)

    def test_update_bookmark_requires_authentication(self):
        bookmark = self.setup_bookmark()
        data = {"url": "https://example.com/"}
        url = reverse("linkding:bookmark-detail", args=[bookmark.id])

        self.put(url, data, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.put(url, data, expected_status_code=status.HTTP_200_OK)

    def test_update_bookmark_only_updates_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        data = {"url": "https://example.com/"}
        url = reverse("linkding:bookmark-detail", args=[bookmark.id])

        self.put(url, data, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_patch_bookmark_requires_authentication(self):
        bookmark = self.setup_bookmark()
        data = {"url": "https://example.com"}
        url = reverse("linkding:bookmark-detail", args=[bookmark.id])

        self.patch(url, data, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)

    def test_patch_bookmark_only_updates_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        data = {"url": "https://example.com"}
        url = reverse("linkding:bookmark-detail", args=[bookmark.id])

        self.patch(url, data, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_delete_bookmark_requires_authentication(self):
        bookmark = self.setup_bookmark()
        url = reverse("linkding:bookmark-detail", args=[bookmark.id])

        self.delete(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)

    def test_archive_requires_authentication(self):
        bookmark = self.setup_bookmark()
        url = reverse("linkding:bookmark-archive", args=[bookmark.id])

        self.post(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.post(url, expected_status_code=status.HTTP_204_NO_CONTENT)

    def test_unarchive_requires_authentication(self):
        bookmark = self.setup_bookmark(is_archived=True)
        url = reverse("linkding:bookmark-unarchive", args=[bookmark.id])

        self.post(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.post(url, expected_status_code=status.HTTP_204_NO_CONTENT)

    def test_check_requires_authentication(self):
        url = reverse("linkding:bookmark-check")
        check_url = urllib.parse.quote_plus("https://example.com")

        self.get(
            f"{url}?url={check_url}", expected_status_code=status.HTTP_401_UNAUTHORIZED
        )

        self.authenticate()
        self.get(f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK)

    def test_user_profile_requires_authentication(self):
        url = reverse("linkding:user-profile")

        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.get(url, expected_status_code=status.HTTP_200_OK)

    def test_singlefile_upload_requires_authentication(self):
        url = reverse("linkding:bookmark-singlefile")

        self.post(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)
