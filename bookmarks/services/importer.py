import logging
from dataclasses import dataclass

from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark, parse_tag_string
from bookmarks.services.parser import parse, NetscapeBookmark
from bookmarks.services.tags import get_or_create_tags
from bookmarks.utils import parse_timestamp

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    total: int = 0
    success: int = 0
    failed: int = 0


def import_netscape_html(html: str, user: User):
    result = ImportResult()

    try:
        netscape_bookmarks = parse(html)
    except:
        logging.exception('Could not read bookmarks file.')
        raise

    for netscape_bookmark in netscape_bookmarks:
        result.total = result.total + 1
        try:
            _import_bookmark_tag(netscape_bookmark, user)
            result.success = result.success + 1
        except:
            shortened_bookmark_tag_str = str(netscape_bookmark)[:100] + '...'
            logging.exception('Error importing bookmark: ' + shortened_bookmark_tag_str)
            result.failed = result.failed + 1

    return result


def _import_bookmark_tag(netscape_bookmark: NetscapeBookmark, user: User):
    # Either modify existing bookmark for the URL or create new one
    bookmark = _get_or_create_bookmark(netscape_bookmark.href, user)

    bookmark.url = netscape_bookmark.href
    if netscape_bookmark.date_added:
        bookmark.date_added = parse_timestamp(netscape_bookmark.date_added)
    else:
        bookmark.date_added = timezone.now()
    bookmark.date_modified = bookmark.date_added
    bookmark.unread = False
    bookmark.title = netscape_bookmark.title
    if netscape_bookmark.description:
        bookmark.description = netscape_bookmark.description
    bookmark.owner = user

    bookmark.full_clean()
    bookmark.save()

    # Set tags
    tag_names = parse_tag_string(netscape_bookmark.tag_string)
    tags = get_or_create_tags(tag_names, user)

    bookmark.tags.set(tags)
    bookmark.save()


def _get_or_create_bookmark(url: str, user: User):
    try:
        return Bookmark.objects.get(url=url, owner=user)
    except Bookmark.DoesNotExist:
        return Bookmark()
