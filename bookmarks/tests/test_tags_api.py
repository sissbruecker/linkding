from django.urls import reverse
from rest_framework import status

from bookmarks.models import Bookmark, Tag
from bookmarks.tests.helpers import BookmarkFactoryMixin, LinkdingApiTestCase


class TagsApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
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

    def test_merge_tags(self):
        self.authenticate()

        target_tag = self.setup_tag(name="target_tag")
        merge_tag1 = self.setup_tag(name="merge_tag1")
        merge_tag2 = self.setup_tag(name="merge_tag2")
        other_tag = self.setup_tag(name="other_tag")

        bookmark1 = self.setup_bookmark(tags=[merge_tag1])
        bookmark2 = self.setup_bookmark(tags=[merge_tag2])
        bookmark3 = self.setup_bookmark(tags=[merge_tag1, merge_tag2])
        bookmark4 = self.setup_bookmark(tags=[merge_tag1, other_tag])
        untouched_bookmark = self.setup_bookmark(tags=[other_tag])

        self.post(
            reverse("linkding:tag-merge", kwargs={"pk": target_tag.id}),
            {"merge_tag_ids": [merge_tag1.id, merge_tag2.id]},
            expected_status_code=status.HTTP_204_NO_CONTENT,
        )

        self.assertTrue(Tag.objects.filter(id=target_tag.id).exists())
        self.assertFalse(Tag.objects.filter(id=merge_tag1.id).exists())
        self.assertFalse(Tag.objects.filter(id=merge_tag2.id).exists())

        self.assertListEqual(list(bookmark1.tags.all()), [target_tag])
        self.assertListEqual(list(bookmark2.tags.all()), [target_tag])
        self.assertListEqual(list(bookmark3.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark4.tags.all()), [target_tag, other_tag])
        self.assertListEqual(list(untouched_bookmark.tags.all()), [other_tag])

    def test_merge_tags_keeps_single_relationship_when_bookmark_has_target_tag(self):
        self.authenticate()

        target_tag = self.setup_tag(name="target_tag")
        merge_tag = self.setup_tag(name="merge_tag")

        bookmark = self.setup_bookmark(tags=[merge_tag, target_tag])

        self.post(
            reverse("linkding:tag-merge", kwargs={"pk": target_tag.id}),
            {"merge_tag_ids": [merge_tag.id]},
            expected_status_code=status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(Tag.objects.filter(id=merge_tag.id).exists())
        self.assertListEqual(list(bookmark.tags.all()), [target_tag])

    def test_merge_tags_requires_merge_tag_ids(self):
        self.authenticate()

        target_tag = self.setup_tag(name="target_tag")
        merge_tag = self.setup_tag(name="merge_tag")

        self.post(
            reverse("linkding:tag-merge", kwargs={"pk": target_tag.id}),
            {},
            expected_status_code=status.HTTP_400_BAD_REQUEST,
        )
        self.post(
            reverse("linkding:tag-merge", kwargs={"pk": target_tag.id}),
            {"merge_tag_ids": []},
            expected_status_code=status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(Tag.objects.filter(id=merge_tag.id).exists())

    def test_can_not_merge_target_tag_into_itself(self):
        self.authenticate()

        target_tag = self.setup_tag(name="target_tag")
        merge_tag = self.setup_tag(name="merge_tag")

        self.post(
            reverse("linkding:tag-merge", kwargs={"pk": target_tag.id}),
            {"merge_tag_ids": [merge_tag.id, target_tag.id]},
            expected_status_code=status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(Tag.objects.filter(id=target_tag.id).exists())
        self.assertTrue(Tag.objects.filter(id=merge_tag.id).exists())

    def test_can_not_merge_tag_that_does_not_exist(self):
        self.authenticate()

        target_tag = self.setup_tag(name="target_tag")
        merge_tag = self.setup_tag(name="merge_tag")

        self.post(
            reverse("linkding:tag-merge", kwargs={"pk": target_tag.id}),
            {"merge_tag_ids": [merge_tag.id, merge_tag.id + 1000]},
            expected_status_code=status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(Tag.objects.filter(id=merge_tag.id).exists())

    def test_can_not_merge_into_tag_of_other_user(self):
        self.authenticate()

        other_user = self.setup_user()
        target_tag = self.setup_tag(name="target_tag", user=other_user)
        merge_tag = self.setup_tag(name="merge_tag")
        bookmark = self.setup_bookmark(tags=[merge_tag])

        self.post(
            reverse("linkding:tag-merge", kwargs={"pk": target_tag.id}),
            {"merge_tag_ids": [merge_tag.id]},
            expected_status_code=status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(Tag.objects.filter(id=target_tag.id).exists())
        self.assertTrue(Tag.objects.filter(id=merge_tag.id).exists())
        self.assertListEqual(list(bookmark.tags.all()), [merge_tag])

    def test_can_not_merge_tag_of_other_user(self):
        self.authenticate()

        other_user = self.setup_user()
        target_tag = self.setup_tag(name="target_tag")
        merge_tag = self.setup_tag(name="merge_tag", user=other_user)
        bookmark = self.setup_bookmark(tags=[merge_tag], user=other_user)

        self.post(
            reverse("linkding:tag-merge", kwargs={"pk": target_tag.id}),
            {"merge_tag_ids": [merge_tag.id]},
            expected_status_code=status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(Tag.objects.filter(id=merge_tag.id).exists())
        self.assertListEqual(list(bookmark.tags.all()), [merge_tag])
