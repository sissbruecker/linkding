from datetime import datetime

import bs4
from bs4 import BeautifulSoup
from django.contrib.auth.models import User

from bookmarks.models import Bookmark, parse_tag_string
from bookmarks.services.tags import get_or_create_tags


def import_netscape_html(html: str, user: User):
    soup = BeautifulSoup(html, 'html.parser')

    bookmark_tags = soup.find_all('dt')

    for bookmark_tag in bookmark_tags:
        _import_bookmark_tag(bookmark_tag, user)


def _import_bookmark_tag(bookmark_tag: bs4.Tag, user: User):
    link_tag = bookmark_tag.a

    if link_tag is None:
        return

    # Either modify existing bookmark for the URL or create new one
    url = link_tag['href']
    bookmark = _get_or_create_bookmark(url, user)

    bookmark.url = url
    add_date = link_tag.get('add_date', datetime.now().timestamp())
    bookmark.date_added = datetime.utcfromtimestamp(int(add_date)).astimezone()
    bookmark.date_modified = bookmark.date_added
    bookmark.unread = link_tag.get('toread', '0') == '1'
    bookmark.title = link_tag.string
    bookmark.owner = user

    bookmark.save()

    # Set tags
    tag_string = link_tag.get('tags', '')
    tag_names = parse_tag_string(tag_string)
    tags = get_or_create_tags(tag_names, user)

    bookmark.tags.set(tags)
    bookmark.save()


def _get_or_create_bookmark(url: str, user: User):
    try:
        return Bookmark.objects.get(url=url, owner=user)
    except Bookmark.DoesNotExist:
        return Bookmark()
