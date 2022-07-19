from django.contrib.syndication.views import Feed

from bookmarks.models import Bookmark


class UnreadBookmarksFeed(Feed):
    title = 'Unread bookmarks'
    description = 'All unread bookmarks'
    link = '/feeds/unread'

    def items(self):
        return Bookmark.objects.filter(unread=True)

    def item_title(self, item):
        return item.resolved_title

    def item_description(self, item):
        return item.resolved_description

    def item_link(self, item):
        return item.url

    def item_pubdate(self, item):
        return item.date_added
