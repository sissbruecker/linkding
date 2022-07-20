from django.contrib.syndication.views import Feed
from django.urls import reverse

from bookmarks.models import Bookmark, FeedToken


class BaseBookmarksFeed(Feed):
    def get_object(self, request, feed_key: str):
        return FeedToken.objects.get(key__exact=feed_key)

    def item_title(self, item: Bookmark):
        return item.resolved_title

    def item_description(self, item: Bookmark):
        return item.resolved_description

    def item_link(self, item: Bookmark):
        return item.url

    def item_pubdate(self, item: Bookmark):
        return item.date_added


class AllBookmarksFeed(BaseBookmarksFeed):
    title = 'All bookmarks'
    description = 'All bookmarks'

    def link(self, feed_token: FeedToken):
        return reverse('bookmarks:feeds.all', args=[feed_token.key])

    def items(self, feed_token: FeedToken):
        return Bookmark.objects.filter(owner=feed_token.user)


class UnreadBookmarksFeed(BaseBookmarksFeed):
    title = 'Unread bookmarks'
    description = 'All unread bookmarks'

    def link(self, feed_token: FeedToken):
        return reverse('bookmarks:feeds.unread', args=[feed_token.key])

    def items(self, feed_token: FeedToken):
        return Bookmark.objects.filter(owner=feed_token.user, unread=True)
