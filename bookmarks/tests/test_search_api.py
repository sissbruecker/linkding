from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from bookmarks.models import UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, LinkdingApiTestCase


class BookmarkSearchApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    def setUp(self):
        token = self.setup_api_token()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        self.url = reverse("linkding:bookmark-search")

    def test_requires_authentication(self):
        self.client.credentials()
        self.get(self.url, expected_status_code=status.HTTP_401_UNAUTHORIZED)

    def test_facets_cover_all_matching_pages(self):
        selected = self.setup_tag(name="Python")
        alpha = self.setup_tag(name="alpha")
        zebra = self.setup_tag(name="Zebra")
        first = self.setup_bookmark(tags=[selected, alpha], title="guide one")
        self.setup_bookmark(tags=[selected, zebra], title="guide two")
        unrelated = self.setup_tag(name="unrelated")
        self.setup_bookmark(tags=[unrelated], title="other")

        response = self.client.get(self.url, {"q": "guide #python", "limit": 1})
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["selected_tag_names"], ["Python"])
        self.assertEqual(response.data["available_tag_names"], ["alpha", "Zebra"])
        self.assertIn("/api/bookmarks/search/", response.data["next"])
        page_two = self.client.get(
            self.url, {"q": "guide #python", "limit": 1, "offset": 1}
        )
        self.assertEqual(page_two.data["results"][0]["id"], first.id)
        self.assertEqual(page_two.data["available_tag_names"], ["alpha", "Zebra"])

    def test_excludes_other_users_and_archived_bookmarks(self):
        own = self.setup_tag(name="own")
        own_bookmark = self.setup_bookmark(tags=[own])
        archived = self.setup_tag(name="archived")
        self.setup_bookmark(tags=[archived], is_archived=True)
        other = User.objects.create_user("other", password="password123")
        private = self.setup_tag(name="private", user=other)
        self.setup_bookmark(tags=[private], user=other, shared=True)

        response = self.get(self.url)
        self.assertEqual([b["id"] for b in response.data["results"]], [own_bookmark.id])
        self.assertEqual(response.data["available_tag_names"], ["own"])
        response = self.client.get(self.url, {"q": "#private"})
        self.assertEqual(response.data["selected_tag_names"], [])
        self.assertEqual(response.data["available_tag_names"], [])

    def test_selected_tags_remain_visible_without_matches(self):
        tag = self.setup_tag(name="Python")
        self.setup_bookmark(tags=[tag], title="guide")
        response = self.client.get(self.url, {"q": "#python missing-content"})
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["selected_tag_names"], ["Python"])
        self.assertEqual(response.data["available_tag_names"], [])

    def test_facets_are_distinct_and_unread_filter_is_applied(self):
        tag = self.setup_tag(name="shared-tag")
        self.setup_bookmark(tags=[tag], unread=True)
        self.setup_bookmark(tags=[tag], unread=True)
        read = self.setup_tag(name="read-only")
        self.setup_bookmark(tags=[read], unread=False)
        response = self.client.get(self.url, {"q": "!unread"})
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["available_tag_names"], ["shared-tag"])

    def test_lax_tag_search_matches_ui_selection(self):
        self.user.profile.tag_search = UserProfile.TAG_SEARCH_LAX
        self.user.profile.save()
        tag = self.setup_tag(name="Python")
        self.setup_bookmark(tags=[tag])
        response = self.client.get(self.url, {"q": "python"})
        self.assertEqual(response.data["selected_tag_names"], ["Python"])
        self.assertEqual(response.data["available_tag_names"], [])

    def test_normal_list_response_is_unchanged(self):
        response = self.get(reverse("linkding:bookmark-list"))
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})

    def test_query_count_does_not_grow_with_result_count(self):
        self.setup_numbered_bookmarks(1, with_tags=True)
        # Warm up request-level configuration caches before comparing query counts.
        self.client.get(self.url, {"limit": 1})
        with CaptureQueriesContext(connection) as small:
            self.client.get(self.url, {"limit": 1})
        self.setup_numbered_bookmarks(30, with_tags=True, tag_prefix="more")
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(self.url, {"limit": 1})
        self.assertEqual(len(small), len(large))
        self.assertEqual(len(response.data["available_tag_names"]), 31)
