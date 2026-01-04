from bs4 import TemplateString
from bs4.element import CData, NavigableString
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark, Tag
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class TagsMergeViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def setUp(self) -> None:
        self.user = self.get_or_create_test_user()
        self.client.force_login(self.user)

    def get_text(self, element):
        # Invalid form responses are wrapped in <template> tags, which BeautifulSoup
        # treats as TemplateString objects. Include those when extracting text.
        return element.get_text(types=(NavigableString, CData, TemplateString))

    def get_form_group(self, response, input_name):
        soup = self.make_soup(response.content.decode())
        input_element = soup.find("input", {"name": input_name})
        if input_element:
            return input_element.find_parent("div", class_="form-group")
        autocomplete_element = soup.find(
            "ld-tag-autocomplete", {"input-name": input_name}
        )
        if autocomplete_element:
            return autocomplete_element.find_parent("div", class_="form-group")
        return None

    def get_autocomplete(self, response, input_name):
        soup = self.make_soup(response.content.decode())
        return soup.find("ld-tag-autocomplete", {"input-name": input_name})

    def test_merge_tags(self):
        target_tag = self.setup_tag(name="target_tag")
        merge_tag1 = self.setup_tag(name="merge_tag1")
        merge_tag2 = self.setup_tag(name="merge_tag2")

        bookmark1 = self.setup_bookmark(tags=[merge_tag1])
        bookmark2 = self.setup_bookmark(tags=[merge_tag2])
        bookmark3 = self.setup_bookmark(tags=[target_tag])

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "target_tag", "merge_tags": "merge_tag1 merge_tag2"},
        )

        self.assertRedirects(response, reverse("linkding:tags.index"))

        self.assertEqual(Tag.objects.count(), 1)
        self.assertFalse(Tag.objects.filter(id=merge_tag1.id).exists())
        self.assertFalse(Tag.objects.filter(id=merge_tag2.id).exists())

        self.assertCountEqual(list(bookmark1.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark2.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark3.tags.all()), [target_tag])

    def test_merge_tags_complex(self):
        target_tag = self.setup_tag(name="target_tag")
        merge_tag1 = self.setup_tag(name="merge_tag1")
        merge_tag2 = self.setup_tag(name="merge_tag2")
        other_tag = self.setup_tag(name="other_tag")

        bookmark1 = self.setup_bookmark(tags=[merge_tag1])
        bookmark2 = self.setup_bookmark(tags=[merge_tag2])
        bookmark3 = self.setup_bookmark(tags=[target_tag])
        bookmark4 = self.setup_bookmark(
            tags=[merge_tag1, merge_tag2]
        )  # both merge tags
        bookmark5 = self.setup_bookmark(
            tags=[merge_tag2, target_tag]
        )  # already has target tag
        bookmark6 = self.setup_bookmark(
            tags=[merge_tag1, merge_tag2, target_tag]
        )  # both merge tags and target
        bookmark7 = self.setup_bookmark(tags=[other_tag])  # unrelated tag
        bookmark8 = self.setup_bookmark(
            tags=[other_tag, merge_tag1]
        )  # merge and unrelated tag
        bookmark9 = self.setup_bookmark(
            tags=[other_tag, target_tag]
        )  # merge and target tag
        bookmark10 = self.setup_bookmark(tags=[])  # no tags

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "target_tag", "merge_tags": "merge_tag1 merge_tag2"},
        )

        self.assertRedirects(response, reverse("linkding:tags.index"))

        self.assertEqual(Bookmark.objects.count(), 10)
        self.assertEqual(Tag.objects.count(), 2)
        self.assertEqual(Bookmark.tags.through.objects.count(), 11)

        self.assertCountEqual(list(Tag.objects.all()), [target_tag, other_tag])

        self.assertCountEqual(list(bookmark1.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark2.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark3.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark4.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark5.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark6.tags.all()), [target_tag])
        self.assertCountEqual(list(bookmark7.tags.all()), [other_tag])
        self.assertCountEqual(list(bookmark8.tags.all()), [other_tag, target_tag])
        self.assertCountEqual(list(bookmark9.tags.all()), [other_tag, target_tag])
        self.assertCountEqual(list(bookmark10.tags.all()), [])

    def test_can_only_merge_own_tags(self):
        other_user = self.setup_user()
        self.setup_tag(name="target_tag", user=other_user)
        self.setup_tag(name="merge_tag", user=other_user)

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "target_tag", "merge_tags": "merge_tag"},
        )

        target_tag_group = self.get_form_group(response, "target_tag")
        self.assertIn(
            'Tag "target_tag" does not exist', self.get_text(target_tag_group)
        )

        merge_tags_group = self.get_form_group(response, "merge_tags")
        self.assertIn('Tag "merge_tag" does not exist', self.get_text(merge_tags_group))

    def test_validate_missing_target_tag(self):
        merge_tag = self.setup_tag(name="merge_tag")

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "", "merge_tags": "merge_tag"},
        )

        target_tag_group = self.get_form_group(response, "target_tag")
        self.assertIn("This field is required", self.get_text(target_tag_group))
        self.assertTrue(Tag.objects.filter(id=merge_tag.id).exists())

        autocomplete = self.get_autocomplete(response, "target_tag")
        self.assertIn("is-error", autocomplete.get("input-class", ""))

    def test_validate_missing_merge_tags(self):
        self.setup_tag(name="target_tag")

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "target_tag", "merge_tags": ""},
        )

        merge_tags_group = self.get_form_group(response, "merge_tags")
        self.assertIn("This field is required", self.get_text(merge_tags_group))

        autocomplete = self.get_autocomplete(response, "merge_tags")
        self.assertIn("is-error", autocomplete.get("input-class", ""))

    def test_validate_nonexistent_target_tag(self):
        self.setup_tag(name="merge_tag")

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "nonexistent_tag", "merge_tags": "merge_tag"},
        )

        target_tag_group = self.get_form_group(response, "target_tag")
        self.assertIn(
            'Tag "nonexistent_tag" does not exist', self.get_text(target_tag_group)
        )

    def test_validate_nonexistent_merge_tag(self):
        self.setup_tag(name="target_tag")
        self.setup_tag(name="merge_tag1")

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "target_tag", "merge_tags": "merge_tag1 nonexistent_tag"},
        )

        merge_tags_group = self.get_form_group(response, "merge_tags")
        self.assertIn(
            'Tag "nonexistent_tag" does not exist', self.get_text(merge_tags_group)
        )

    def test_validate_multiple_target_tags(self):
        self.setup_tag(name="target_tag1")
        self.setup_tag(name="target_tag2")

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "target_tag1 target_tag2", "merge_tags": "some_tag"},
        )

        target_tag_group = self.get_form_group(response, "target_tag")
        self.assertIn(
            "Please enter only one tag name for the target tag",
            self.get_text(target_tag_group),
        )

    def test_validate_target_tag_in_merge_list(self):
        self.setup_tag(name="target_tag")
        self.setup_tag(name="merge_tag")

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "target_tag", "merge_tags": "target_tag merge_tag"},
        )

        merge_tags_group = self.get_form_group(response, "merge_tags")
        self.assertIn(
            "The target tag cannot be selected for merging",
            self.get_text(merge_tags_group),
        )

    def test_merge_shows_success_message(self):
        self.setup_tag(name="target_tag")
        self.setup_tag(name="merge_tag1")
        self.setup_tag(name="merge_tag2")

        response = self.client.post(
            reverse("linkding:tags.merge"),
            {"target_tag": "target_tag", "merge_tags": "merge_tag1 merge_tag2"},
            follow=True,
        )

        self.assertInHTML(
            """
                <div class="toast toast-success" role="alert">
                    Successfully merged 2 tags (merge_tag1, merge_tag2) into "target_tag".
                </div>
            """,
            response.content.decode(),
        )
