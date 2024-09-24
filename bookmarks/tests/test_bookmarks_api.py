import urllib.parse
from collections import OrderedDict
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from bookmarks.models import Bookmark, BookmarkSearch, UserProfile
from bookmarks.services import website_loader
from bookmarks.services.website_loader import WebsiteMetadata
from bookmarks.tests.helpers import LinkdingApiTestCase, BookmarkFactoryMixin


class BookmarksApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):

    def authenticate(self):
        self.api_token = Token.objects.get_or_create(
            user=self.get_or_create_test_user()
        )[0]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.api_token.key)

    def assertBookmarkListEqual(self, data_list, bookmarks):
        expectations = []
        for bookmark in bookmarks:
            tag_names = [tag.name for tag in bookmark.tags.all()]
            tag_names.sort(key=str.lower)
            expectation = OrderedDict()
            expectation["id"] = bookmark.id
            expectation["url"] = bookmark.url
            expectation["title"] = bookmark.title
            expectation["description"] = bookmark.description
            expectation["notes"] = bookmark.notes
            expectation["web_archive_snapshot_url"] = bookmark.web_archive_snapshot_url
            expectation["favicon_url"] = (
                f"http://testserver/static/{bookmark.favicon_file}"
                if bookmark.favicon_file
                else None
            )
            expectation["preview_image_url"] = (
                f"http://testserver/static/{bookmark.preview_image_file}"
                if bookmark.preview_image_file
                else None
            )
            expectation["is_archived"] = bookmark.is_archived
            expectation["unread"] = bookmark.unread
            expectation["shared"] = bookmark.shared
            expectation["tag_names"] = tag_names
            expectation["date_added"] = bookmark.date_added.isoformat().replace(
                "+00:00", "Z"
            )
            expectation["date_modified"] = bookmark.date_modified.isoformat().replace(
                "+00:00", "Z"
            )
            expectation["website_title"] = None
            expectation["website_description"] = None
            expectations.append(expectation)

        for data in data_list:
            data["tag_names"].sort(key=str.lower)

        self.assertCountEqual(data_list, expectations)

    def test_list_bookmarks(self):
        self.authenticate()
        bookmarks = self.setup_numbered_bookmarks(5)

        response = self.get(
            reverse("bookmarks:bookmark-list"), expected_status_code=status.HTTP_200_OK
        )
        self.assertBookmarkListEqual(response.data["results"], bookmarks)

    def test_list_bookmarks_with_more_details(self):
        self.authenticate()
        bookmarks = self.setup_numbered_bookmarks(
            5,
            with_tags=True,
            with_web_archive_snapshot_url=True,
            with_favicon_file=True,
            with_preview_image_file=True,
        )

        response = self.get(
            reverse("bookmarks:bookmark-list"), expected_status_code=status.HTTP_200_OK
        )
        self.assertBookmarkListEqual(response.data["results"], bookmarks)

    def test_list_bookmarks_returns_none_for_website_title_and_description(self):
        self.authenticate()
        bookmark = self.setup_bookmark()
        bookmark.website_title = "Website title"
        bookmark.website_description = "Website description"
        bookmark.save()

        response = self.get(
            reverse("bookmarks:bookmark-list"), expected_status_code=status.HTTP_200_OK
        )
        self.assertIsNone(response.data["results"][0]["website_title"])
        self.assertIsNone(response.data["results"][0]["website_description"])

    def test_list_bookmarks_does_not_return_archived_bookmarks(self):
        self.authenticate()
        bookmarks = self.setup_numbered_bookmarks(5)
        self.setup_numbered_bookmarks(5, archived=True)

        response = self.get(
            reverse("bookmarks:bookmark-list"), expected_status_code=status.HTTP_200_OK
        )
        self.assertBookmarkListEqual(response.data["results"], bookmarks)

    def test_list_bookmarks_should_filter_by_query(self):
        self.authenticate()
        search_value = self.get_random_string()
        bookmarks = self.setup_numbered_bookmarks(5, prefix=search_value)
        self.setup_numbered_bookmarks(5)

        response = self.get(
            reverse("bookmarks:bookmark-list") + "?q=" + search_value,
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], bookmarks)

    def test_list_bookmarks_filter_unread(self):
        self.authenticate()
        unread_bookmarks = self.setup_numbered_bookmarks(5, unread=True)
        read_bookmarks = self.setup_numbered_bookmarks(5, unread=False)

        # Filter off
        response = self.get(
            reverse("bookmarks:bookmark-list"), expected_status_code=status.HTTP_200_OK
        )
        self.assertBookmarkListEqual(
            response.data["results"], unread_bookmarks + read_bookmarks
        )

        # Filter shared
        response = self.get(
            reverse("bookmarks:bookmark-list") + "?unread=yes",
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], unread_bookmarks)

        # Filter unshared
        response = self.get(
            reverse("bookmarks:bookmark-list") + "?unread=no",
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], read_bookmarks)

    def test_list_bookmarks_filter_shared(self):
        self.authenticate()
        unshared_bookmarks = self.setup_numbered_bookmarks(5)
        shared_bookmarks = self.setup_numbered_bookmarks(5, shared=True)

        # Filter off
        response = self.get(
            reverse("bookmarks:bookmark-list"), expected_status_code=status.HTTP_200_OK
        )
        self.assertBookmarkListEqual(
            response.data["results"], unshared_bookmarks + shared_bookmarks
        )

        # Filter shared
        response = self.get(
            reverse("bookmarks:bookmark-list") + "?shared=yes",
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], shared_bookmarks)

        # Filter unshared
        response = self.get(
            reverse("bookmarks:bookmark-list") + "?shared=no",
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], unshared_bookmarks)

    def test_list_bookmarks_should_respect_sort(self):
        self.authenticate()
        bookmarks = self.setup_numbered_bookmarks(5)
        bookmarks.reverse()

        response = self.get(
            reverse("bookmarks:bookmark-list") + "?sort=title_desc",
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], bookmarks)

    def test_list_archived_bookmarks_does_not_return_unarchived_bookmarks(self):
        self.authenticate()
        self.setup_numbered_bookmarks(5)
        archived_bookmarks = self.setup_numbered_bookmarks(5, archived=True)

        response = self.get(
            reverse("bookmarks:bookmark-archived"),
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], archived_bookmarks)

    def test_list_archived_bookmarks_with_more_details(self):
        self.authenticate()
        archived_bookmarks = self.setup_numbered_bookmarks(
            5,
            archived=True,
            with_tags=True,
            with_web_archive_snapshot_url=True,
            with_favicon_file=True,
            with_preview_image_file=True,
        )

        response = self.get(
            reverse("bookmarks:bookmark-archived"),
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], archived_bookmarks)

    def test_list_archived_bookmarks_should_filter_by_query(self):
        self.authenticate()
        search_value = self.get_random_string()
        archived_bookmarks = self.setup_numbered_bookmarks(
            5, archived=True, prefix=search_value
        )
        self.setup_numbered_bookmarks(5, archived=True)

        response = self.get(
            reverse("bookmarks:bookmark-archived") + "?q=" + search_value,
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], archived_bookmarks)

    def test_list_archived_bookmarks_should_respect_sort(self):
        self.authenticate()
        bookmarks = self.setup_numbered_bookmarks(5, archived=True)
        bookmarks.reverse()

        response = self.get(
            reverse("bookmarks:bookmark-archived") + "?sort=title_desc",
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], bookmarks)

    def test_list_shared_bookmarks(self):
        self.authenticate()

        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        user4 = self.setup_user(enable_sharing=False)
        shared_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user2),
            self.setup_bookmark(shared=True, user=user3),
        ]
        # Unshared bookmarks
        self.setup_bookmark(shared=False, user=user1)
        self.setup_bookmark(shared=False, user=user2)
        self.setup_bookmark(shared=False, user=user3)
        self.setup_bookmark(shared=True, user=user4)

        response = self.get(
            reverse("bookmarks:bookmark-shared"),
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], shared_bookmarks)

    def test_list_shared_bookmarks_with_more_details(self):
        self.authenticate()

        other_user = self.setup_user(enable_sharing=True)
        shared_bookmarks = self.setup_numbered_bookmarks(
            5,
            shared=True,
            user=other_user,
            with_tags=True,
            with_web_archive_snapshot_url=True,
            with_favicon_file=True,
            with_preview_image_file=True,
        )

        response = self.get(
            reverse("bookmarks:bookmark-shared"),
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], shared_bookmarks)

    def test_list_only_publicly_shared_bookmarks_when_not_logged_in(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True)

        shared_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user1),
        ]
        self.setup_bookmark(shared=True, user=user2)
        self.setup_bookmark(shared=True, user=user2)

        response = self.get(
            reverse("bookmarks:bookmark-shared"),
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], shared_bookmarks)

    def test_list_shared_bookmarks_should_filter_by_query_and_user(self):
        self.authenticate()

        # Search by query
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        expected_bookmarks = [
            self.setup_bookmark(title="searchvalue", shared=True, user=user1),
            self.setup_bookmark(title="searchvalue", shared=True, user=user2),
            self.setup_bookmark(title="searchvalue", shared=True, user=user3),
        ]
        self.setup_bookmark(shared=True, user=user1),
        self.setup_bookmark(shared=True, user=user2),
        self.setup_bookmark(shared=True, user=user3),

        response = self.get(
            reverse("bookmarks:bookmark-shared") + "?q=searchvalue",
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], expected_bookmarks)

        # Search by user
        user_search_user = self.setup_user(enable_sharing=True)
        expected_bookmarks = [
            self.setup_bookmark(shared=True, user=user_search_user),
            self.setup_bookmark(shared=True, user=user_search_user),
            self.setup_bookmark(shared=True, user=user_search_user),
        ]
        response = self.get(
            reverse("bookmarks:bookmark-shared") + "?user=" + user_search_user.username,
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], expected_bookmarks)

        # Search by query and user
        combined_search_user = self.setup_user(enable_sharing=True)
        expected_bookmarks = [
            self.setup_bookmark(
                title="searchvalue", shared=True, user=combined_search_user
            ),
            self.setup_bookmark(
                title="searchvalue", shared=True, user=combined_search_user
            ),
            self.setup_bookmark(
                title="searchvalue", shared=True, user=combined_search_user
            ),
        ]
        response = self.get(
            reverse("bookmarks:bookmark-shared")
            + "?q=searchvalue&user="
            + combined_search_user.username,
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], expected_bookmarks)

    def test_list_shared_bookmarks_should_respect_sort(self):
        self.authenticate()
        user = self.setup_user(enable_sharing=True)
        bookmarks = self.setup_numbered_bookmarks(5, shared=True, user=user)
        bookmarks.reverse()

        response = self.get(
            reverse("bookmarks:bookmark-shared") + "?sort=title_desc",
            expected_status_code=status.HTTP_200_OK,
        )
        self.assertBookmarkListEqual(response.data["results"], bookmarks)

    def test_create_bookmark(self):
        self.authenticate()

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
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertEqual(bookmark.url, data["url"])
        self.assertEqual(bookmark.title, data["title"])
        self.assertEqual(bookmark.description, data["description"])
        self.assertEqual(bookmark.notes, data["notes"])
        self.assertFalse(bookmark.is_archived, data["is_archived"])
        self.assertFalse(bookmark.unread, data["unread"])
        self.assertFalse(bookmark.shared, data["shared"])
        self.assertEqual(bookmark.tags.count(), 2)
        self.assertEqual(bookmark.tags.filter(name=data["tag_names"][0]).count(), 1)
        self.assertEqual(bookmark.tags.filter(name=data["tag_names"][1]).count(), 1)

    def test_create_bookmark_enhances_with_metadata_by_default(self):
        self.authenticate()

        data = {"url": "https://example.com/"}
        with patch.object(website_loader, "load_website_metadata") as mock_load:
            mock_load.return_value = WebsiteMetadata(
                url="https://example.com/",
                title="Website title",
                description="Website description",
                preview_image=None,
            )
            self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertEqual(bookmark.title, "Website title")
        self.assertEqual(bookmark.description, "Website description")

    def test_create_bookmark_does_not_enhance_with_metadata_if_scraping_is_disabled(
        self,
    ):
        self.authenticate()

        data = {"url": "https://example.com/"}
        with patch.object(website_loader, "load_website_metadata") as mock_load:
            mock_load.return_value = WebsiteMetadata(
                url="https://example.com/",
                title="Website title",
                description="Website description",
                preview_image=None,
            )
            self.post(
                reverse("bookmarks:bookmark-list") + "?disable_scraping",
                data,
                status.HTTP_201_CREATED,
            )
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertEqual(bookmark.title, "")
        self.assertEqual(bookmark.description, "")

    def test_create_bookmark_with_same_url_updates_existing_bookmark(self):
        self.authenticate()

        original_bookmark = self.setup_bookmark()
        data = {
            "url": original_bookmark.url,
            "title": "Updated title",
            "description": "Updated description",
            "notes": "Updated notes",
            "unread": True,
            "shared": True,
            "is_archived": True,
            "tag_names": ["tag1", "tag2"],
        }
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertEqual(bookmark.id, original_bookmark.id)
        self.assertEqual(bookmark.url, data["url"])
        self.assertEqual(bookmark.title, data["title"])
        self.assertEqual(bookmark.description, data["description"])
        self.assertEqual(bookmark.notes, data["notes"])
        # Saving a duplicate bookmark should not modify archive flag - right?
        self.assertFalse(bookmark.is_archived)
        self.assertEqual(bookmark.unread, data["unread"])
        self.assertEqual(bookmark.shared, data["shared"])
        self.assertEqual(bookmark.tags.count(), 2)
        self.assertEqual(bookmark.tags.filter(name=data["tag_names"][0]).count(), 1)
        self.assertEqual(bookmark.tags.filter(name=data["tag_names"][1]).count(), 1)

    def test_create_bookmark_replaces_whitespace_in_tag_names(self):
        self.authenticate()

        data = {
            "url": "https://example.com/",
            "title": "Test title",
            "description": "Test description",
            "tag_names": ["tag 1", "tag 2"],
        }
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        tag_names = [tag.name for tag in bookmark.tags.all()]
        self.assertListEqual(tag_names, ["tag-1", "tag-2"])

    def test_create_bookmark_minimal_payload(self):
        self.authenticate()

        data = {"url": "https://example.com/"}
        self.post(
            reverse("bookmarks:bookmark-list") + "?disable_scraping",
            data,
            status.HTTP_201_CREATED,
        )

        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertEqual(data["url"], bookmark.url)
        self.assertEqual("", bookmark.title)
        self.assertEqual("", bookmark.description)
        self.assertEqual("", bookmark.notes)
        self.assertFalse(bookmark.is_archived)
        self.assertFalse(bookmark.unread)
        self.assertFalse(bookmark.shared)
        self.assertBookmarkListEqual([], bookmark.tag_names)

    def test_create_archived_bookmark(self):
        self.authenticate()

        data = {
            "url": "https://example.com/",
            "title": "Test title",
            "description": "Test description",
            "is_archived": True,
            "tag_names": ["tag1", "tag2"],
        }
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertEqual(bookmark.url, data["url"])
        self.assertEqual(bookmark.title, data["title"])
        self.assertEqual(bookmark.description, data["description"])
        self.assertTrue(bookmark.is_archived)
        self.assertEqual(bookmark.tags.count(), 2)
        self.assertEqual(bookmark.tags.filter(name=data["tag_names"][0]).count(), 1)
        self.assertEqual(bookmark.tags.filter(name=data["tag_names"][1]).count(), 1)

    def test_create_bookmark_is_not_archived_by_default(self):
        self.authenticate()

        data = {"url": "https://example.com/"}
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertFalse(bookmark.is_archived)

    def test_create_unread_bookmark(self):
        self.authenticate()

        data = {"url": "https://example.com/", "unread": True}
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertTrue(bookmark.unread)

    def test_create_bookmark_is_not_unread_by_default(self):
        self.authenticate()

        data = {"url": "https://example.com/"}
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertFalse(bookmark.unread)

    def test_create_shared_bookmark(self):
        self.authenticate()

        data = {"url": "https://example.com/", "shared": True}
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertTrue(bookmark.shared)

    def test_create_bookmark_is_not_shared_by_default(self):
        self.authenticate()

        data = {"url": "https://example.com/"}
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertFalse(bookmark.shared)

    def test_create_bookmark_should_add_tags_from_auto_tagging(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        self.authenticate()
        profile = self.get_or_create_test_user().profile
        profile.auto_tagging_rules = f"example.com {tag2.name}"
        profile.save()

        data = {"url": "https://example.com/", "tag_names": [tag1.name]}
        self.post(reverse("bookmarks:bookmark-list"), data, status.HTTP_201_CREATED)
        bookmark = Bookmark.objects.get(url=data["url"])
        self.assertCountEqual(bookmark.tags.all(), [tag1, tag2])

    def test_get_bookmark(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual([response.data], [bookmark])

    def test_get_bookmark_with_more_details(self):
        self.authenticate()
        tag1 = self.setup_tag()
        bookmark = self.setup_bookmark(
            web_archive_snapshot_url="https://web.archive.org/web/1/",
            tags=[tag1],
        )

        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertBookmarkListEqual([response.data], [bookmark])

    def test_update_bookmark(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        data = {"url": "https://example.com/updated"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertEqual(updated_bookmark.url, data["url"])

    def test_update_bookmark_ignores_readonly_fields(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        data = {
            "url": "https://example.com/updated",
            "web_archive_snapshot_url": "test",
            "website_title": "test",
            "website_description": "test",
        }
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertEqual(data["url"], updated_bookmark.url)
        self.assertNotEqual(
            data["web_archive_snapshot_url"], updated_bookmark.web_archive_snapshot_url
        )
        self.assertNotEqual(data["website_title"], updated_bookmark.website_title)
        self.assertNotEqual(
            data["website_description"], updated_bookmark.website_description
        )

    def test_update_bookmark_fails_without_required_fields(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        data = {"title": "https://example.com/"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_400_BAD_REQUEST)

    def test_update_bookmark_with_minimal_payload_does_not_modify_bookmark(self):
        self.authenticate()
        bookmark = self.setup_bookmark(
            is_archived=True, unread=True, shared=True, tags=[self.setup_tag()]
        )

        data = {"url": "https://example.com/"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertEqual(updated_bookmark.url, data["url"])
        self.assertEqual(updated_bookmark.title, bookmark.title)
        self.assertEqual(updated_bookmark.description, bookmark.description)
        self.assertEqual(updated_bookmark.notes, bookmark.notes)
        self.assertEqual(updated_bookmark.is_archived, bookmark.is_archived)
        self.assertEqual(updated_bookmark.unread, bookmark.unread)
        self.assertEqual(updated_bookmark.shared, bookmark.shared)
        self.assertListEqual(updated_bookmark.tag_names, bookmark.tag_names)

    def test_update_bookmark_unread_flag(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        data = {"url": "https://example.com/", "unread": True}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertEqual(updated_bookmark.unread, True)

    def test_update_bookmark_shared_flag(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        data = {"url": "https://example.com/", "shared": True}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertEqual(updated_bookmark.shared, True)

    def test_update_bookmark_adds_tags_from_auto_tagging(self):
        bookmark = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        self.authenticate()
        profile = self.get_or_create_test_user().profile
        profile.auto_tagging_rules = f"example.com {tag2.name}"
        profile.save()

        data = {"url": "https://example.com/", "tag_names": [tag1.name]}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertCountEqual(updated_bookmark.tags.all(), [tag1, tag2])

    def test_update_bookmark_should_prevent_duplicate_urls(self):
        self.authenticate()
        edited_bookmark = self.setup_bookmark(url="https://example.com/edited")
        existing_bookmark = self.setup_bookmark(url="https://example.com/existing")
        other_user_bookmark = self.setup_bookmark(
            url="https://example.com/other", user=self.setup_user()
        )

        # if the URL isn't modified it's not a duplicate
        data = {"url": edited_bookmark.url}
        url = reverse("bookmarks:bookmark-detail", args=[edited_bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)

        # if the URL is already bookmarked by another user, it's not a duplicate
        data = {"url": other_user_bookmark.url}
        url = reverse("bookmarks:bookmark-detail", args=[edited_bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_200_OK)

        # if the URL is already bookmarked by the same user, it's a duplicate
        data = {"url": existing_bookmark.url}
        url = reverse("bookmarks:bookmark-detail", args=[edited_bookmark.id])
        self.put(url, data, expected_status_code=status.HTTP_400_BAD_REQUEST)

    def test_patch_bookmark(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        data = {"url": "https://example.com"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.url, data["url"])

        data = {"title": "Updated title"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.title, data["title"])

        data = {"description": "Updated description"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.description, data["description"])

        data = {"notes": "Updated notes"}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.notes, data["notes"])

        data = {"unread": True}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertTrue(bookmark.unread)

        data = {"unread": False}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertFalse(bookmark.unread)

        data = {"shared": True}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertTrue(bookmark.shared)

        data = {"shared": False}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertFalse(bookmark.shared)

        data = {"tag_names": ["updated-tag-1", "updated-tag-2"]}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        bookmark.refresh_from_db()
        tag_names = [tag.name for tag in bookmark.tags.all()]
        self.assertListEqual(tag_names, ["updated-tag-1", "updated-tag-2"])

    def test_patch_ignores_readonly_fields(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        data = {
            "web_archive_snapshot_url": "test",
            "website_title": "test",
            "website_description": "test",
        }
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertNotEqual(
            data["web_archive_snapshot_url"], updated_bookmark.web_archive_snapshot_url
        )
        self.assertNotEqual(data["website_title"], updated_bookmark.website_title)
        self.assertNotEqual(
            data["website_description"], updated_bookmark.website_description
        )

    def test_patch_with_empty_payload_does_not_modify_bookmark(self):
        self.authenticate()
        bookmark = self.setup_bookmark(
            is_archived=True, unread=True, shared=True, tags=[self.setup_tag()]
        )

        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, {}, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertEqual(updated_bookmark.url, bookmark.url)
        self.assertEqual(updated_bookmark.title, bookmark.title)
        self.assertEqual(updated_bookmark.description, bookmark.description)
        self.assertEqual(updated_bookmark.notes, bookmark.notes)
        self.assertEqual(updated_bookmark.is_archived, bookmark.is_archived)
        self.assertEqual(updated_bookmark.unread, bookmark.unread)
        self.assertEqual(updated_bookmark.shared, bookmark.shared)
        self.assertListEqual(updated_bookmark.tag_names, bookmark.tag_names)

    def test_patch_bookmark_adds_tags_from_auto_tagging(self):
        bookmark = self.setup_bookmark()
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()

        self.authenticate()
        profile = self.get_or_create_test_user().profile
        profile.auto_tagging_rules = f"example.com {tag2.name}"
        profile.save()

        data = {"tag_names": [tag1.name]}
        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.patch(url, data, expected_status_code=status.HTTP_200_OK)
        updated_bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertCountEqual(updated_bookmark.tags.all(), [tag1, tag2])

    def test_delete_bookmark(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        url = reverse("bookmarks:bookmark-detail", args=[bookmark.id])
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(Bookmark.objects.filter(id=bookmark.id)), 0)

    def test_archive(self):
        self.authenticate()
        bookmark = self.setup_bookmark()

        url = reverse("bookmarks:bookmark-archive", args=[bookmark.id])
        self.post(url, expected_status_code=status.HTTP_204_NO_CONTENT)
        bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertTrue(bookmark.is_archived)

    def test_unarchive(self):
        self.authenticate()
        bookmark = self.setup_bookmark(is_archived=True)

        url = reverse("bookmarks:bookmark-unarchive", args=[bookmark.id])
        self.post(url, expected_status_code=status.HTTP_204_NO_CONTENT)
        bookmark = Bookmark.objects.get(id=bookmark.id)
        self.assertFalse(bookmark.is_archived)

    def test_check_returns_no_bookmark_if_url_is_not_bookmarked(self):
        self.authenticate()

        url = reverse("bookmarks:bookmark-check")
        check_url = urllib.parse.quote_plus("https://example.com")
        response = self.get(
            f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK
        )
        bookmark_data = response.data["bookmark"]

        self.assertIsNone(bookmark_data)

    def test_check_returns_scraped_metadata_if_url_is_not_bookmarked(self):
        self.authenticate()

        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            expected_metadata = WebsiteMetadata(
                "https://example.com",
                "Scraped metadata",
                "Scraped description",
                "https://example.com/preview.png",
            )
            mock_load_website_metadata.return_value = expected_metadata

            url = reverse("bookmarks:bookmark-check")
            check_url = urllib.parse.quote_plus("https://example.com")
            response = self.get(
                f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK
            )
            metadata = response.data["metadata"]

            self.assertIsNotNone(metadata)
            self.assertEqual(expected_metadata.url, metadata["url"])
            self.assertEqual(expected_metadata.title, metadata["title"])
            self.assertEqual(expected_metadata.description, metadata["description"])
            self.assertEqual(expected_metadata.preview_image, metadata["preview_image"])

    def test_check_returns_bookmark_if_url_is_bookmarked(self):
        self.authenticate()

        bookmark = self.setup_bookmark(
            url="https://example.com",
            title="Example title",
            description="Example description",
            favicon_file="favicon.png",
            preview_image_file="preview.png",
        )

        url = reverse("bookmarks:bookmark-check")
        check_url = urllib.parse.quote_plus("https://example.com")
        response = self.get(
            f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK
        )
        bookmark_data = response.data["bookmark"]

        self.assertIsNotNone(bookmark_data)
        self.assertEqual(bookmark.id, bookmark_data["id"])
        self.assertEqual(bookmark.url, bookmark_data["url"])
        self.assertEqual(bookmark.title, bookmark_data["title"])
        self.assertEqual(bookmark.description, bookmark_data["description"])
        self.assertEqual(
            "http://testserver/static/favicon.png", bookmark_data["favicon_url"]
        )
        self.assertEqual(
            "http://testserver/static/preview.png", bookmark_data["preview_image_url"]
        )

    def test_check_returns_scraped_metadata_if_url_is_bookmarked(self):
        self.authenticate()

        self.setup_bookmark(
            url="https://example.com",
        )

        with patch.object(
            website_loader, "load_website_metadata"
        ) as mock_load_website_metadata:
            expected_metadata = WebsiteMetadata(
                "https://example.com",
                "Scraped metadata",
                "Scraped description",
                "https://example.com/preview.png",
            )
            mock_load_website_metadata.return_value = expected_metadata

            url = reverse("bookmarks:bookmark-check")
            check_url = urllib.parse.quote_plus("https://example.com")
            response = self.get(
                f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK
            )
            metadata = response.data["metadata"]

            self.assertIsNotNone(metadata)
            self.assertEqual(expected_metadata.url, metadata["url"])
            self.assertEqual(expected_metadata.title, metadata["title"])
            self.assertEqual(expected_metadata.description, metadata["description"])
            self.assertEqual(expected_metadata.preview_image, metadata["preview_image"])

    def test_check_returns_no_auto_tags_if_none_configured(self):
        self.authenticate()

        url = reverse("bookmarks:bookmark-check")
        check_url = urllib.parse.quote_plus("https://example.com")
        response = self.get(
            f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK
        )
        auto_tags = response.data["auto_tags"]

        self.assertCountEqual(auto_tags, [])

    def test_check_returns_matching_auto_tags(self):
        self.authenticate()

        profile = self.get_or_create_test_user().profile
        profile.auto_tagging_rules = "example.com tag1 tag2"
        profile.save()

        url = reverse("bookmarks:bookmark-check")
        check_url = urllib.parse.quote_plus("https://example.com")
        response = self.get(
            f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK
        )
        auto_tags = response.data["auto_tags"]

        self.assertCountEqual(auto_tags, ["tag1", "tag2"])

    def test_can_only_access_own_bookmarks(self):
        self.authenticate()
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True)

        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        inaccessible_bookmark = self.setup_bookmark(user=other_user)
        inaccessible_shared_bookmark = self.setup_bookmark(user=other_user, shared=True)
        self.setup_bookmark(user=other_user, is_archived=True)

        url = reverse("bookmarks:bookmark-list")
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        url = reverse("bookmarks:bookmark-archived")
        response = self.get(url, expected_status_code=status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        url = reverse("bookmarks:bookmark-detail", args=[inaccessible_bookmark.id])
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse(
            "bookmarks:bookmark-detail", args=[inaccessible_shared_bookmark.id]
        )
        self.get(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse("bookmarks:bookmark-detail", args=[inaccessible_bookmark.id])
        self.put(
            url,
            {url: "https://example.com/"},
            expected_status_code=status.HTTP_404_NOT_FOUND,
        )
        self.patch(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse(
            "bookmarks:bookmark-detail", args=[inaccessible_shared_bookmark.id]
        )
        self.put(
            url,
            {url: "https://example.com/"},
            expected_status_code=status.HTTP_404_NOT_FOUND,
        )
        self.patch(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse("bookmarks:bookmark-detail", args=[inaccessible_bookmark.id])
        self.delete(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse(
            "bookmarks:bookmark-detail", args=[inaccessible_shared_bookmark.id]
        )
        self.delete(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse("bookmarks:bookmark-archive", args=[inaccessible_bookmark.id])
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse(
            "bookmarks:bookmark-archive", args=[inaccessible_shared_bookmark.id]
        )
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse("bookmarks:bookmark-unarchive", args=[inaccessible_bookmark.id])
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse(
            "bookmarks:bookmark-unarchive", args=[inaccessible_shared_bookmark.id]
        )
        self.post(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        url = reverse("bookmarks:bookmark-check")
        check_url = urllib.parse.quote_plus(inaccessible_bookmark.url)
        response = self.get(
            f"{url}?url={check_url}", expected_status_code=status.HTTP_200_OK
        )
        self.assertIsNone(response.data["bookmark"])

    def assertUserProfile(self, response: Response, profile: UserProfile):
        self.assertEqual(response.data["theme"], profile.theme)
        self.assertEqual(
            response.data["bookmark_date_display"], profile.bookmark_date_display
        )
        self.assertEqual(
            response.data["bookmark_link_target"], profile.bookmark_link_target
        )
        self.assertEqual(
            response.data["web_archive_integration"], profile.web_archive_integration
        )
        self.assertEqual(response.data["tag_search"], profile.tag_search)
        self.assertEqual(response.data["enable_sharing"], profile.enable_sharing)
        self.assertEqual(
            response.data["enable_public_sharing"], profile.enable_public_sharing
        )
        self.assertEqual(response.data["enable_favicons"], profile.enable_favicons)
        self.assertEqual(response.data["display_url"], profile.display_url)
        self.assertEqual(response.data["permanent_notes"], profile.permanent_notes)
        self.assertEqual(
            response.data["search_preferences"], profile.search_preferences
        )

    def test_user_profile(self):
        self.authenticate()

        # default profile
        profile = self.user.profile
        url = reverse("bookmarks:user-profile")
        response = self.get(url, expected_status_code=status.HTTP_200_OK)

        self.assertUserProfile(response, profile)

        # update profile
        profile.theme = "dark"
        profile.bookmark_date_display = "absolute"
        profile.bookmark_link_target = "_self"
        profile.web_archive_integration = "enabled"
        profile.tag_search = "lax"
        profile.enable_sharing = True
        profile.enable_public_sharing = True
        profile.enable_favicons = True
        profile.display_url = True
        profile.permanent_notes = True
        profile.search_preferences = {
            "sort": BookmarkSearch.SORT_TITLE_ASC,
            "shared": BookmarkSearch.FILTER_SHARED_OFF,
            "unread": BookmarkSearch.FILTER_UNREAD_YES,
        }
        profile.save()

        url = reverse("bookmarks:user-profile")
        response = self.get(url, expected_status_code=status.HTTP_200_OK)

        self.assertUserProfile(response, profile)
