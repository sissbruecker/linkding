import unicodedata
from dataclasses import dataclass

from django.contrib.syndication.views import Feed
from django.db.models import QuerySet
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import Bookmark, BookmarkSearch, FeedToken, UserProfile


@dataclass
class FeedContext:
    feed_token: FeedToken | None
    query_set: QuerySet[Bookmark]


def sanitize(text: str):
    if not text:
        return ""
    # remove control characters
    valid_chars = ["\n", "\r", "\t"]
    return "".join(
        ch for ch in text if ch in valid_chars or unicodedata.category(ch)[0] != "C"
    )


class BaseBookmarksFeed(Feed):
    def get_object(self, request, feed_key: str):
        feed_token = FeedToken.objects.get(key__exact=feed_key)
        search = BookmarkSearch(q=request.GET.get("q", ""))
        query_set = queries.query_bookmarks(
            feed_token.user, feed_token.user.profile, search
        )
        return FeedContext(feed_token, query_set)

    def item_title(self, item: Bookmark):
        return sanitize(item.resolved_title)

    def item_description(self, item: Bookmark):
        return sanitize(item.resolved_description)

    def item_link(self, item: Bookmark):
        return item.url

    def item_pubdate(self, item: Bookmark):
        return item.date_added


class AllBookmarksFeed(BaseBookmarksFeed):
    title = "All bookmarks"
    description = "All bookmarks"

    def link(self, context: FeedContext):
        return reverse("bookmarks:feeds.all", args=[context.feed_token.key])

    def items(self, context: FeedContext):
        return context.query_set


class UnreadBookmarksFeed(BaseBookmarksFeed):
    title = "Unread bookmarks"
    description = "All unread bookmarks"

    def link(self, context: FeedContext):
        return reverse("bookmarks:feeds.unread", args=[context.feed_token.key])

    def items(self, context: FeedContext):
        return context.query_set.filter(unread=True)


class SharedBookmarksFeed(BaseBookmarksFeed):
    title = "Shared bookmarks"
    description = "All shared bookmarks"

    def get_object(self, request, feed_key: str):
        feed_token = FeedToken.objects.get(key__exact=feed_key)
        search = BookmarkSearch(q=request.GET.get("q", ""))
        query_set = queries.query_shared_bookmarks(
            None, feed_token.user.profile, search, False
        )
        return FeedContext(feed_token, query_set)

    def link(self, context: FeedContext):
        return reverse("bookmarks:feeds.shared", args=[context.feed_token.key])

    def items(self, context: FeedContext):
        return context.query_set


class PublicSharedBookmarksFeed(BaseBookmarksFeed):
    title = "Public shared bookmarks"
    description = "All public shared bookmarks"

    def get_object(self, request):
        search = BookmarkSearch(q=request.GET.get("q", ""))
        default_profile = UserProfile()
        query_set = queries.query_shared_bookmarks(None, default_profile, search, True)
        return FeedContext(None, query_set)

    def link(self, context: FeedContext):
        return reverse("bookmarks:feeds.public_shared")

    def items(self, context: FeedContext):
        return context.query_set
