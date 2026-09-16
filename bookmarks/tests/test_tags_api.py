from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from bookmarks.models import Bookmark, Tag
from bookmarks.tests.helpers import BookmarkFactoryMixin, LinkdingApiTestCase


class TagsApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    def test_list_with_counts(self):
        self.authenticate()
        tag = self.setup_tag()
        empty_tag = self.setup_tag()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag], is_archived=True)
        other_user = self.setup_user()
        other_tag = self.setup_tag(user=other_user)
        self.setup_bookmark(tags=[other_tag, tag], user=other_user)

        response = self.get(reverse("linkding:tag-list") + "?with_counts=true")

        counts = {
            item["id"]: item["bookmark_count"] for item in response.data["results"]
        }
        self.assertEqual(counts, {tag.id: 2, empty_tag.id: 0})

    def test_counts_are_opt_in(self):
        self.authenticate()
        self.setup_tag()
        for query in ("", "?with_counts=false"):
            with self.subTest(query=query):
                response = self.get(reverse("linkding:tag-list") + query)
                self.assertNotIn("bookmark_count", response.data["results"][0])

    def test_retrieve_with_counts(self):
        self.authenticate()
        tag = self.setup_tag()
        self.setup_bookmark(tags=[tag])
        url = reverse("linkding:tag-detail", kwargs={"pk": tag.id})
        self.assertEqual(self.get(url + "?with_counts=true").data["bookmark_count"], 1)
        self.assertNotIn("bookmark_count", self.get(url).data)

        other_tag = self.setup_tag(user=self.setup_user())
        url = reverse("linkding:tag-detail", kwargs={"pk": other_tag.id})
        self.get(
            url + "?with_counts=true", expected_status_code=status.HTTP_404_NOT_FOUND
        )

    def test_count_queries_do_not_grow_with_tag_count(self):
        self.authenticate()
        self.setup_bookmark(tags=[self.setup_tag()])
        url = reverse("linkding:tag-list") + "?with_counts=true"
        # Warm up authentication and lazy application initialization.
        self.get(url)
        with CaptureQueriesContext(connection) as single:
            self.get(url)
        for _ in range(10):
            self.setup_bookmark(tags=[self.setup_tag()])
        with CaptureQueriesContext(connection) as multiple:
            response = self.get(url)
        self.assertEqual(len(single), len(multiple))
        self.assertEqual(len(response.data["results"]), 11)
        self.assertTrue(
            all(item["bookmark_count"] == 1 for item in response.data["results"])
        )

    def test_counts_preserve_pagination(self):
        self.authenticate()
        for _ in range(3):
            self.setup_bookmark(tags=[self.setup_tag()])
        response = self.get(
            reverse("linkding:tag-list") + "?with_counts=true&limit=1&offset=1"
        )
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["bookmark_count"], 1)

    def test_delete_tag(self):
        self.authenticate()

        tag = self.setup_tag()

        url = reverse("linkding:tag-detail", kwargs={"pk": tag.id})
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)

        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_delete_tag_keeps_tagged_bookmarks(self):
        self.authenticate()

        tag = self.setup_tag()
        bookmark = self.setup_bookmark(tags=[tag])

        url = reverse("linkding:tag-detail", kwargs={"pk": tag.id})
        self.delete(url, expected_status_code=status.HTTP_204_NO_CONTENT)

        self.assertFalse(Tag.objects.filter(id=tag.id).exists())
        self.assertTrue(Bookmark.objects.filter(id=bookmark.id).exists())
        self.assertEqual(bookmark.tags.count(), 0)

    def test_can_not_delete_tag_of_other_user(self):
        self.authenticate()

        other_user = self.setup_user()
        tag = self.setup_tag(user=other_user)

        url = reverse("linkding:tag-detail", kwargs={"pk": tag.id})
        self.delete(url, expected_status_code=status.HTTP_404_NOT_FOUND)

        self.assertTrue(Tag.objects.filter(id=tag.id).exists())
