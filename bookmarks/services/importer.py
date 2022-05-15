import logging
from dataclasses import dataclass
from typing import List

from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark, parse_tag_string
from bookmarks.services import tasks
from bookmarks.services.parser import parse, NetscapeBookmark
from bookmarks.services.tags import get_or_create_tag
from bookmarks.utils import parse_timestamp

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    total: int = 0
    success: int = 0
    failed: int = 0


class TagCache:
    def __init__(self, user: User):
        self.user = user
        self.cache = dict()

    def get(self, tag_names: List[str]):
        result = []
        for tag_name in tag_names:
            tag_name_lowercase = tag_name.lower()
            if tag_name_lowercase in self.cache:
                tag = self.cache[tag_name_lowercase]
            else:
                tag = get_or_create_tag(tag_name, self.user)
                self.cache[tag_name_lowercase] = tag

            # Prevent adding duplicates
            if not (tag in result):
                result.append(tag)

        return result


def import_netscape_html(html: str, user: User):
    result = ImportResult()
    start = timezone.now()
    tag_cache = TagCache(user)

    try:
        netscape_bookmarks = parse(html)
    except:
        logging.exception('Could not read bookmarks file.')
        raise

    parse_end = timezone.now()
    print('Parse duration: ', parse_end - start)

    batches = _get_batches(netscape_bookmarks, 100)
    for batch in batches:
        _import_batch(batch, user, tag_cache, result)

    # Create snapshots for newly imported bookmarks
    tasks.schedule_bookmarks_without_snapshots(user)

    end = timezone.now()
    print('Import duration: ', end - start)

    return result


def _get_batches(items: List, batch_size: int):
    batches = []
    offset = 0
    num_items = len(items)

    while offset < num_items:
        batch = items[offset:min(offset + batch_size, num_items)]
        if len(batch) > 0:
            batches.append(batch)
        offset = offset + batch_size

    return batches


def _import_batch(netscape_bookmarks: List[NetscapeBookmark], user: User, tag_cache: TagCache, result: ImportResult):
    # Query existing bookmarks
    batch_urls = [bookmark.href for bookmark in netscape_bookmarks]
    existing_bookmarks = Bookmark.objects.filter(owner=user, url__in=batch_urls)

    for netscape_bookmark in netscape_bookmarks:
        result.total = result.total + 1
        try:
            existing_bookmark = next(
                (bookmark for bookmark in existing_bookmarks if bookmark.url == netscape_bookmark.href), None)
            _import_netscape_bookmark(netscape_bookmark, existing_bookmark, user, tag_cache)
            result.success = result.success + 1
        except:
            shortened_bookmark_tag_str = str(netscape_bookmark)[:100] + '...'
            logging.exception('Error importing bookmark: ' + shortened_bookmark_tag_str)
            result.failed = result.failed + 1


def _import_netscape_bookmark(netscape_bookmark: NetscapeBookmark, existing_bookmark: Bookmark, user: User,
                              tag_cache: TagCache):
    # Either modify existing bookmark for the URL or create new one
    bookmark = existing_bookmark if existing_bookmark else Bookmark()

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

    # bookmark.full_clean()
    bookmark.save()

    # Set tags
    tag_names = parse_tag_string(netscape_bookmark.tag_string)
    tags = tag_cache.get(tag_names)

    bookmark.tags.set(tags)
    bookmark.save()


def _get_or_create_bookmark(url: str, user: User):
    try:
        return Bookmark.objects.get(url=url, owner=user)
    except Bookmark.DoesNotExist:
        return Bookmark()
