import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bookmarks.models import Tag
from bookmarks.services.tags import get_or_create_tag, get_or_create_tags

User = get_user_model()


class TagServiceTestCase(TestCase):

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            "testuser", "test@example.com", "password123"
        )

    def test_get_or_create_tag_should_create_new_tag(self):
        get_or_create_tag("Book", self.user)

        tags = Tag.objects.all()

        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].name, "Book")
        self.assertEqual(tags[0].owner, self.user)
        self.assertTrue(
            abs(tags[0].date_added - timezone.now()) < datetime.timedelta(seconds=10)
        )

    def test_get_or_create_tag_should_return_existing_tag(self):
        first_tag = get_or_create_tag("Book", self.user)
        second_tag = get_or_create_tag("Book", self.user)

        tags = Tag.objects.all()

        self.assertEqual(len(tags), 1)
        self.assertEqual(first_tag.id, second_tag.id)

    def test_get_or_create_tag_should_ignore_casing_when_looking_for_existing_tag(self):
        first_tag = get_or_create_tag("Book", self.user)
        second_tag = get_or_create_tag("book", self.user)

        tags = Tag.objects.all()

        self.assertEqual(len(tags), 1)
        self.assertEqual(first_tag.id, second_tag.id)

    def test_get_or_create_tag_should_handle_legacy_dbs_with_existing_duplicates(self):
        first_tag = Tag.objects.create(
            name="book", date_added=timezone.now(), owner=self.user
        )
        Tag.objects.create(name="Book", date_added=timezone.now(), owner=self.user)
        retrieved_tag = get_or_create_tag("Book", self.user)

        self.assertEqual(first_tag.id, retrieved_tag.id)

    def test_get_or_create_tags_should_return_tags(self):
        books_tag = get_or_create_tag("Book", self.user)
        movies_tag = get_or_create_tag("Movie", self.user)

        tags = get_or_create_tags(["book", "movie"], self.user)

        self.assertEqual(len(tags), 2)
        self.assertListEqual(tags, [books_tag, movies_tag])

    def test_get_or_create_tags_should_deduplicate_tags(self):
        books_tag = get_or_create_tag("Book", self.user)

        tags = get_or_create_tags(["book", "Book", "BOOK"], self.user)

        self.assertEqual(len(tags), 1)
        self.assertListEqual(tags, [books_tag])
