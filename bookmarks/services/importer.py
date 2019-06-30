from datetime import datetime

import bs4
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark, Tag


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
    bookmark.date_added = datetime.utcfromtimestamp(int(link_tag['add_date']))
    bookmark.date_modified = bookmark.date_added
    bookmark.unread = link_tag['toread'] == '1'
    bookmark.title = link_tag.string
    bookmark.owner = user

    bookmark.save()

    # Set tags
    tag_string = link_tag['tags']
    tag_names = tag_string.strip().split(',')

    tags = [_get_or_create_tag(tag_name, user) for tag_name in tag_names]
    bookmark.tags.set(tags)
    bookmark.save()


def _get_or_create_bookmark(url: str, user: User):
    try:
        return Bookmark.objects.get(url=url, owner=user)
    except Bookmark.DoesNotExist:
        return Bookmark()


def _get_or_create_tag(name: str, user: User):
    try:
        return Tag.objects.get(name=name, owner=user)
    except Tag.DoesNotExist:
        tag = Tag(name=name, owner=user)
        tag.date_added = timezone.now()
        tag.save()
        return tag
