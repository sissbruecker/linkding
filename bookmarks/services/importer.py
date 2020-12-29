import logging
from dataclasses import dataclass
from datetime import datetime

import bs4
from bs4 import BeautifulSoup
from django.contrib.auth.models import User

from bookmarks.models import Bookmark, parse_tag_string
from bookmarks.services.tags import get_or_create_tags

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    total: int = 0
    success: int = 0
    failed: int = 0


def import_netscape_html(html: str, user: User):
    result = ImportResult()

    try:
        soup = BeautifulSoup(html, 'html.parser')
    except:
        logging.exception('Could not read bookmarks file.')
        raise

    bookmark_tags = soup.find_all('dt')

    for bookmark_tag in bookmark_tags:
        result.total = result.total + 1
        try:
            _import_bookmark_tag(bookmark_tag, user)
            result.success = result.success + 1
        except:
            shortened_bookmark_tag_str = str(bookmark_tag)[:100] + '...'
            logging.exception('Error importing bookmark: ' + shortened_bookmark_tag_str)
            result.failed = result.failed + 1

    return result


def _import_bookmark_tag(bookmark_tag: bs4.Tag, user: User):
    link_tag = bookmark_tag.a

    if link_tag is None:
        return

    # Either modify existing bookmark for the URL or create new one
    url = link_tag['href']
    description = _extract_description(bookmark_tag)
    bookmark = _get_or_create_bookmark(url, user)

    bookmark.url = url
    add_date = link_tag.get('add_date', datetime.now().timestamp())
    bookmark.date_added = datetime.utcfromtimestamp(int(add_date)).astimezone()
    bookmark.date_modified = bookmark.date_added
    bookmark.unread = link_tag.get('toread', '0') == '1'
    bookmark.title = link_tag.string
    if description:
        bookmark.description = description
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


def _extract_description(bookmark_tag: bs4.Tag):
    """
    Since the Netscape HTML format has no closing tags, all following bookmark tags are part of the description tag
    so to extract the description text we have to get creative. For now we combine the text of all text nodes until we
    detect a <dt> tag which indicates a new bookmark
    :param bookmark_tag:
    :return:
    """
    description_tag = bookmark_tag.find('dd', recursive=False)

    if description_tag is None:
        return None

    description = ''

    for content in description_tag.contents:
        if type(content) is bs4.element.Tag and content.name == 'dt':
            break
        if type(content) is bs4.element.NavigableString:
            description += content

    return description.strip()
