import unicodedata
from dataclasses import dataclass

from django.contrib.syndication.views import Feed
from django.db.models import QuerySet, prefetch_related_objects
from django.http import HttpRequest
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import Bookmark, BookmarkSearch, FeedToken, UserProfile


@dataclass
class FeedContext:
    request: HttpRequest
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
    def get_object(self, request, feed_key: str | None):
        feed_token = FeedToken.objects.get(key__exact=feed_key) if feed_key else None
        search = BookmarkSearch(
            q=request.GET.get("q", ""),
            unread=request.GET.get("unread", ""),
            shared=request.GET.get("shared", ""),
        )
        query_set = self.get_query_set(feed_token, search)
        return FeedContext(request, feed_token, query_set)

    def get_query_set(self, feed_token: FeedToken, search: BookmarkSearch):
        raise NotImplementedError

    def items(self, context: FeedContext):
        limit = context.request.GET.get("limit", 100)
        if limit:
            data = context.query_set[: int(limit)]
        else:
            data = list(context.query_set)
        prefetch_related_objects(data, "tags")
        return data

    def item_title(self, item: Bookmark):
        return sanitize(item.resolved_title)

    def item_description(self, item: Bookmark):
        return sanitize(item.resolved_description)

    def item_link(self, item: Bookmark):
        return item.url

    def item_pubdate(self, item: Bookmark):
        return item.date_added

    def item_categories(self, item: Bookmark):
        return item.tag_names


class AllBookmarksFeed(BaseBookmarksFeed):
    title = "All bookmarks"
    description = "All bookmarks"

    def get_query_set(self, feed_token: FeedToken, search: BookmarkSearch):
        return queries.query_bookmarks(feed_token.user, feed_token.user.profile, search)

    def link(self, context: FeedContext):
        return reverse("bookmarks:feeds.all", args=[context.feed_token.key])


class UnreadBookmarksFeed(BaseBookmarksFeed):
    title = "Unread bookmarks"
    description = "All unread bookmarks"

    def get_query_set(self, feed_token: FeedToken, search: BookmarkSearch):
        return queries.query_bookmarks(
            feed_token.user, feed_token.user.profile, search
        ).filter(unread=True)

    def link(self, context: FeedContext):
        return reverse("bookmarks:feeds.unread", args=[context.feed_token.key])


class SharedBookmarksFeed(BaseBookmarksFeed):
    title = "Shared bookmarks"
    description = "All shared bookmarks"

    def get_query_set(self, feed_token: FeedToken, search: BookmarkSearch):
        return queries.query_shared_bookmarks(
            None, feed_token.user.profile, search, False
        )

    def link(self, context: FeedContext):
        return reverse("bookmarks:feeds.shared", args=[context.feed_token.key])


class PublicSharedBookmarksFeed(BaseBookmarksFeed):
    title = "Public shared bookmarks"
    description = "All public shared bookmarks"

    def get_object(self, request):
        return super().get_object(request, None)

    def get_query_set(self, feed_token: FeedToken, search: BookmarkSearch):
        return queries.query_shared_bookmarks(None, UserProfile(), search, True)

    def link(self, context: FeedContext):
        return reverse("bookmarks:feeds.public_shared")
