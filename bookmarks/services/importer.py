from datetime import datetime

from bs4 import BeautifulSoup, Tag
from django.contrib.auth.models import User

from bookmarks.models import Bookmark


def import_netscape_html(html: str, user: User):
    soup = BeautifulSoup(html, 'html.parser')

    bookmark_tags = soup.find_all('dt')

    for bookmark_tag in bookmark_tags:
        _import_bookmark_tag(bookmark_tag, user)


def _import_bookmark_tag(bookmark_tag: Tag, user: User):
    link_tag = bookmark_tag.a

    if link_tag is None:
        return

    # Either modify existing bookmark for the URL or create new one
    url = link_tag['href']
    bookmark = _get_or_create_bookmark(url, user)

    bookmark.url = url
    bookmark.date_added = datetime.utcfromtimestamp(int(link_tag['add_date']))
    bookmark.date_modified = bookmark.date_added
    bookmark.unread = link_tag['toread'] == '1'
    bookmark.title = link_tag.string
    bookmark.owner = user

    bookmark.save()


def _get_or_create_bookmark(url: str, user: User):
    try:
        return Bookmark.objects.get(url=url, owner=user)
    except Bookmark.DoesNotExist:
        return Bookmark()
