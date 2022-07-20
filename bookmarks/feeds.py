from dataclasses import dataclass

from django.contrib.syndication.views import Feed
from django.db.models import QuerySet
from django.urls import reverse

from bookmarks.models import Bookmark, FeedToken
from bookmarks import queries


@dataclass
class FeedContext:
    feed_token: FeedToken
    query_set: QuerySet[Bookmark]


class BaseBookmarksFeed(Feed):
    def get_object(self, request, feed_key: str):
        feed_token = FeedToken.objects.get(key__exact=feed_key)
        query_string = request.GET.get('q')
        query_set = queries.query_bookmarks(feed_token.user, query_string)
        return FeedContext(feed_token, query_set)

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

    def link(self, context: FeedContext):
        return reverse('bookmarks:feeds.all', args=[context.feed_token.key])

    def items(self, context: FeedContext):
        return context.query_set


class UnreadBookmarksFeed(BaseBookmarksFeed):
    title = 'Unread bookmarks'
    description = 'All unread bookmarks'

    def link(self, context: FeedContext):
        return reverse('bookmarks:feeds.unread', args=[context.feed_token.key])

    def items(self, context: FeedContext):
        return context.query_set.filter(unread=True)
