import urllib.parse

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from bookmarks.tests.helpers import LinkdingApiTestCase, BookmarkFactoryMixin


class BookmarksApiPermissionsTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    def authenticate(self) -> None:
        self.api_token = Token.objects.get_or_create(
            user=self.get_or_create_test_user()
        )[0]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.api_token.key)

    def test_list_bookmarks_requires_authentication(self):
        self.get(
            reverse("bookmarks:bookmark-list"),
            expected_status_code=status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate()
        self.get(
            reverse("bookmarks:bookmark-list"), expected_status_code=status.HTTP_200_OK
        )

    def test_list_archived_bookmarks_requires_authentication(self):
        self.get(
            reverse("bookmarks:bookmark-archived"),
            expected_status_code=status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate()
        self.get(
            reverse("bookmarks:bookmark-archived"),
            expected_status_code=status.HTTP_200_OK,
        )

    def test_list_shared_bookmarks_does_not_require_authentication(self):
        self.get(
            reverse("bookmarks:bookmark-shared"),
            expected_status_code=status.HTTP_200_OK,
        )

        self.authenticate()
        self.get(
            reverse("bookmarks:bookmark-shared"),
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

        self.post(
            reverse("bookmarks:bookmark-list"), data, status.HTTP_401_UNAUTHORIZED
        )

        self.authenticate()
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)

    def test_get_bookmark_requires_authentication(self):
        bookmark = self.setup_bookmark()
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])

        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.get(url, expected_status_code=status.HTTP_200_OK)

    def test_update_bookmark_requires_authentication(self):
        bookmark = self.setup_bookmark()
        data = {"url": "https://example.com/"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])

        self.put(url, data, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.put(url, data, expected_status_code=status.HTTP_200_OK)

    def test_update_bookmark_only_updates_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        data = {"url": "https://example.com/"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])

        self.put(url, data, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_patch_bookmark_requires_authentication(self):
        bookmark = self.setup_bookmark()
        data = {"url": "https://example.com"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])

        self.patch(url, data, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)

    def test_patch_bookmark_only_updates_own_bookmarks(self):
        self.authenticate()

        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        data = {"url": "https://example.com"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])

        self.patch(url, data, expected_status_code=status.HTTP_404_NOT_FOUND)

    def test_delete_bookmark_requires_authentication(self):
        bookmark = self.setup_bookmark()
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])

        self.delete(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)

    def test_archive_requires_authentication(self):
        bookmark = self.setup_bookmark()
        url = reverse("bookmarks:bookmark-archive", args=[bookmark.id])

        self.post(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.post(url, expected_status_code=status.HTTP_204_NO_CONTENT)

    def test_unarchive_requires_authentication(self):
        bookmark = self.setup_bookmark(is_archived=True)
        url = reverse("bookmarks:bookmark-unarchive", args=[bookmark.id])

        self.post(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.post(url, expected_status_code=status.HTTP_204_NO_CONTENT)

    def test_check_requires_authentication(self):
        url = reverse("bookmarks:bookmark-check")
        check_url = urllib.parse.quote_plus("https://example.com")

        self.get(
            f"{url}?url={check_url}", expected_status_code=status.HTTP_401_UNAUTHORIZED
        )

        self.authenticate()
        self.get(f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK)

    def test_user_profile_requires_authentication(self):
        url = reverse("bookmarks:user-profile")

        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

        self.authenticate()
        self.get(url, expected_status_code=status.HTTP_200_OK)
