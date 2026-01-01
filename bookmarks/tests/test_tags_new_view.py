from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Tag
from bookmarks.tests.helpers import BookmarkFactoryMixin


class TagsNewViewTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self) -> None:
        self.user = self.get_or_create_test_user()
        self.client.force_login(self.user)

    def test_create_tag(self):
        response = self.client.post(reverse("linkding:tags.new"), {"name": "new_tag"})

        self.assertRedirects(response, reverse("linkding:tags.index"))
        self.assertEqual(Tag.objects.count(), 1)
        self.assertTrue(Tag.objects.filter(name="new_tag", owner=self.user).exists())

    def test_show_error_for_empty_name(self):
        response = self.client.post(reverse("linkding:tags.new"), {"name": ""})

        self.assertContains(response, "This field is required")
        self.assertEqual(Tag.objects.count(), 0)

    def test_show_error_for_duplicate_name(self):
        self.setup_tag(name="existing_tag")

        response = self.client.post(
            reverse("linkding:tags.new"), {"name": "existing_tag"}
        )

        self.assertContains(response, "Tag &quot;existing_tag&quot; already exists")
        self.assertEqual(Tag.objects.count(), 1)

    def test_show_error_for_duplicate_name_different_casing(self):
        self.setup_tag(name="existing_tag")

        response = self.client.post(
            reverse("linkding:tags.new"), {"name": "existing_TAG"}
        )

        self.assertContains(response, "Tag &quot;existing_TAG&quot; already exists")
        self.assertEqual(Tag.objects.count(), 1)

    def test_no_error_for_duplicate_name_different_user(self):
        other_user = self.setup_user()
        self.setup_tag(name="existing_tag", user=other_user)

        response = self.client.post(
            reverse("linkding:tags.new"), {"name": "existing_tag"}
        )

        self.assertRedirects(response, reverse("linkding:tags.index"))
        self.assertEqual(Tag.objects.count(), 2)
        self.assertEqual(
            Tag.objects.filter(name="existing_tag", owner=self.user).count(), 1
        )
        self.assertEqual(
            Tag.objects.filter(name="existing_tag", owner=other_user).count(), 1
        )

    def test_create_shows_success_message(self):
        response = self.client.post(
            reverse("linkding:tags.new"), {"name": "new_tag"}, follow=True
        )

        self.assertInHTML(
            """
            <div class="toast toast-success" role="alert">
                Tag "new_tag" created successfully.
            </div>
        """,
            response.content.decode(),
        )
