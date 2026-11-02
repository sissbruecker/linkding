
from django.contrib.auth.models import User
from django.test import TestCase

from bookmarks.forms import TagForm


class TagEmojiTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="joe",
            password="123"
        )

    def test_tag_can_be_created_with_unicode_emoji(self):
        form = TagForm(
            user=self.user,
            data={
                "name": "programing",
                "emoji": "💻"
            }
        )

        self.assertIn("emoji", form.fields)

        self.assertTrue(form.is_valid(), form.errors)

        tag = form.save()

        tag.refresh_from_db()

        self.assertEqual(tag.emoji, "💻")
        self.assertEqual(tag.name, "programing")
