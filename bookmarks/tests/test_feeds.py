import datetime
import email

from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin
from bookmarks.models import FeedToken, User


def rfc2822_date(date):
    if not isinstance(date, datetime.datetime):
        date = datetime.datetime.combine(date, datetime.time())
    return email.utils.format_datetime(date)


class FeedsTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)
        self.token = FeedToken.objects.get_or_create(user=user)[0]

    def test_unread_returns_404_for_unknown_feed_token(self):
        response = self.client.get(reverse('bookmarks:feeds.unread', args=['foo']))

        self.assertEqual(response.status_code, 404)

    def test_unread_metadata(self):
        feed_url = reverse('bookmarks:feeds.unread', args=[self.token.key])
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, '<title>Unread bookmarks</title>')
        self.assertContains(response, '<description>All unread bookmarks</description>')
        self.assertContains(response, f'<link>http://testserver{feed_url}</link>')
        self.assertContains(response, f'<atom:link href="http://testserver{feed_url}" rel="self"></atom:link>')

    def test_unread_returns_unread_bookmarks(self):
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)

        unread_bookmarks = [
            self.setup_bookmark(unread=True),
            self.setup_bookmark(unread=True),
            self.setup_bookmark(unread=True),
        ]

        response = self.client.get(reverse('bookmarks:feeds.unread', args=[self.token.key]))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, '<title>Unread bookmarks</title>')
        self.assertContains(response, '<item>', count=len(unread_bookmarks))

        for bookmark in unread_bookmarks:
            expected_item = '<item>' \
                            f'<title>{bookmark.resolved_title}</title>' \
                            f'<link>{bookmark.url}</link>' \
                            f'<description>{bookmark.resolved_description}</description>' \
                            f'<pubDate>{rfc2822_date(bookmark.date_added)}</pubDate>' \
                            f'<guid>{bookmark.url}</guid>' \
                            '</item>'
            self.assertContains(response, expected_item, count=1)

    def test_unread_returns_only_user_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)

        response = self.client.get(reverse('bookmarks:feeds.unread', args=[self.token.key]))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, '<item>', count=0)
