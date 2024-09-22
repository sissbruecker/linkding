import datetime
import email
import urllib.parse

from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin
from bookmarks.models import FeedToken, User
from bookmarks.feeds import sanitize


def rfc2822_date(date):
    if not isinstance(date, datetime.datetime):
        date = datetime.datetime.combine(date, datetime.time())
    return email.utils.format_datetime(date)


class FeedsTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)
        self.token = FeedToken.objects.get_or_create(user=user)[0]

    def assertFeedItems(self, response, bookmarks):
        self.assertContains(response, "<item>", count=len(bookmarks))

        for bookmark in bookmarks:
            categories = []
            for tag in bookmark.tag_names:
                categories.append(f"<category>{tag}</category>")

            if bookmark.resolved_description:
                expected_description = (
                    f"<description>{bookmark.resolved_description}</description>"
                )
            else:
                expected_description = "<description/>"

            expected_item = (
                "<item>"
                f"<title>{bookmark.resolved_title}</title>"
                f"<link>{bookmark.url}</link>"
                f"{expected_description}"
                f"<pubDate>{rfc2822_date(bookmark.date_added)}</pubDate>"
                f"<guid>{bookmark.url}</guid>"
                f"{''.join(categories)}"
                "</item>"
            )
            self.assertContains(response, expected_item, count=1)

    def test_all_returns_404_for_unknown_feed_token(self):
        response = self.client.get(reverse("bookmarks:feeds.all", args=["foo"]))

        self.assertEqual(response.status_code, 404)

    def test_all_metadata(self):
        feed_url = reverse("bookmarks:feeds.all", args=[self.token.key])
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<title>All bookmarks</title>")
        self.assertContains(response, "<description>All bookmarks</description>")
        self.assertContains(response, f"<link>http://testserver{feed_url}</link>")
        self.assertContains(
            response, f'<atom:link href="http://testserver{feed_url}" rel="self"/>'
        )

    def test_all_returns_all_unarchived_bookmarks(self):
        bookmarks = [
            self.setup_bookmark(description="test description"),
            self.setup_bookmark(description=""),
            self.setup_bookmark(unread=True, description="test description"),
        ]
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)

        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, bookmarks)

    def test_all_returns_only_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)

        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<item>", count=0)

    def test_unread_returns_404_for_unknown_feed_token(self):
        response = self.client.get(reverse("bookmarks:feeds.unread", args=["foo"]))

        self.assertEqual(response.status_code, 404)

    def test_unread_metadata(self):
        feed_url = reverse("bookmarks:feeds.unread", args=[self.token.key])
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<title>Unread bookmarks</title>")
        self.assertContains(response, "<description>All unread bookmarks</description>")
        self.assertContains(response, f"<link>http://testserver{feed_url}</link>")
        self.assertContains(
            response, f'<atom:link href="http://testserver{feed_url}" rel="self"/>'
        )

    def test_unread_returns_unread_and_unarchived_bookmarks(self):
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=True, is_archived=True)
        self.setup_bookmark(unread=True, is_archived=True)
        self.setup_bookmark(unread=False, is_archived=True)

        unread_bookmarks = [
            self.setup_bookmark(unread=True, description="test description"),
            self.setup_bookmark(unread=True, description=""),
            self.setup_bookmark(unread=True, description="test description"),
        ]

        response = self.client.get(
            reverse("bookmarks:feeds.unread", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, unread_bookmarks)

    def test_unread_returns_only_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)

        response = self.client.get(
            reverse("bookmarks:feeds.unread", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<item>", count=0)

    def test_shared_returns_404_for_unknown_feed_token(self):
        response = self.client.get(reverse("bookmarks:feeds.shared", args=["foo"]))

        self.assertEqual(response.status_code, 404)

    def test_shared_metadata(self):
        feed_url = reverse("bookmarks:feeds.shared", args=[self.token.key])
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<title>Shared bookmarks</title>")
        self.assertContains(response, "<description>All shared bookmarks</description>")
        self.assertContains(response, f"<link>http://testserver{feed_url}</link>")
        self.assertContains(
            response, f'<atom:link href="http://testserver{feed_url}" rel="self"/>'
        )

    def test_shared_returns_shared_bookmarks_only(self):
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=False)

        self.setup_bookmark()
        self.setup_bookmark(shared=False, user=user1)
        self.setup_bookmark(shared=True, user=user2)

        shared_bookmarks = [
            self.setup_bookmark(shared=True, user=user1, description="test"),
            self.setup_bookmark(shared=True, user=user1, description="test"),
            self.setup_bookmark(shared=True, user=user1, description="test"),
        ]

        response = self.client.get(
            reverse("bookmarks:feeds.shared", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, shared_bookmarks)

    def test_public_shared_does_not_require_auth(self):
        response = self.client.get(reverse("bookmarks:feeds.public_shared"))

        self.assertEqual(response.status_code, 200)

    def test_public_shared_metadata(self):
        feed_url = reverse("bookmarks:feeds.public_shared")
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<title>Public shared bookmarks</title>")
        self.assertContains(
            response, "<description>All public shared bookmarks</description>"
        )
        self.assertContains(response, f"<link>http://testserver{feed_url}</link>")
        self.assertContains(
            response, f'<atom:link href="http://testserver{feed_url}" rel="self"/>'
        )

    def test_public_shared_returns_publicly_shared_bookmarks_only(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=False)

        self.setup_bookmark()
        self.setup_bookmark(shared=False, user=user1)
        self.setup_bookmark(shared=False, user=user2)
        self.setup_bookmark(shared=True, user=user2)
        self.setup_bookmark(shared=True, user=user3)

        public_shared_bookmarks = [
            self.setup_bookmark(shared=True, user=user1, description="test"),
            self.setup_bookmark(shared=True, user=user1, description="test"),
            self.setup_bookmark(shared=True, user=user1, description="test"),
        ]

        response = self.client.get(reverse("bookmarks:feeds.public_shared"))
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, public_shared_bookmarks)

    def test_with_query(self):
        tag1 = self.setup_tag()
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark(tags=[tag1])
        bookmark3 = self.setup_bookmark(tags=[tag1])

        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        feed_url = reverse("bookmarks:feeds.all", args=[self.token.key])

        url = feed_url + f"?q={bookmark1.title}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=1)
        self.assertContains(response, f"<guid>{bookmark1.url}</guid>", count=1)

        url = feed_url + "?q=" + urllib.parse.quote("#" + tag1.name)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=2)
        self.assertContains(response, f"<guid>{bookmark2.url}</guid>", count=1)
        self.assertContains(response, f"<guid>{bookmark3.url}</guid>", count=1)

        url = feed_url + "?q=" + urllib.parse.quote(f"#{tag1.name} {bookmark2.title}")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=1)
        self.assertContains(response, f"<guid>{bookmark2.url}</guid>", count=1)

    def test_unread_parameter(self):
        self.setup_bookmark(unread=True),
        self.setup_bookmark(unread=True),
        self.setup_bookmark(unread=False),
        self.setup_bookmark(unread=False),
        self.setup_bookmark(unread=False),
        self.setup_bookmark(unread=False),

        # without unread parameter
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=6)

        # with unread=yes
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key]) + "?unread=yes"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=2)

        # with unread=no
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key]) + "?unread=no"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=4)

    def test_shared_parameter(self):
        self.setup_bookmark(shared=True)
        self.setup_bookmark(shared=True)
        self.setup_bookmark(shared=False)
        self.setup_bookmark(shared=False)
        self.setup_bookmark(shared=False)
        self.setup_bookmark(shared=False)

        # without shared parameter
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=6)

        # with shared=yes
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key]) + "?shared=yes"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=2)

        # with shared=no
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key]) + "?shared=no"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=4)

    def test_with_tags(self):
        bookmarks = [
            self.setup_bookmark(description="test description"),
            self.setup_bookmark(
                description="test description",
                tags=[self.setup_tag(), self.setup_tag()],
            ),
        ]

        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, bookmarks)

    def test_with_limit(self):
        self.setup_numbered_bookmarks(200)

        # without limit - defaults to 100
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=100)

        # with increased limit
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key]) + "?limit=200"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=200)

        # with decreased limit
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key]) + "?limit=5"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=5)

    def test_strip_control_characters(self):
        self.setup_bookmark(
            title="test\n\r\t\0\x08title", description="test\n\r\t\0\x08description"
        )
        response = self.client.get(
            reverse("bookmarks:feeds.all", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=1)
        self.assertContains(response, f"<title>test\n\r\ttitle</title>", count=1)
        self.assertContains(
            response, f"<description>test\n\r\tdescription</description>", count=1
        )

    def test_sanitize_with_none_text(self):
        self.assertEqual("", sanitize(None))
