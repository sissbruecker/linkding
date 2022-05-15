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

    # Split bookmarks to import into batches, to keep memory usage for bulk operations manageable
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

    # Create or update bookmarks from parsed Netscape bookmarks
    bookmarks_to_create = []
    bookmarks_to_update = []

    for netscape_bookmark in netscape_bookmarks:
        result.total = result.total + 1
        try:
            bookmark = next(
                (bookmark for bookmark in existing_bookmarks if bookmark.url == netscape_bookmark.href), None)
            if not bookmark:
                bookmark = Bookmark(owner=user)
                is_update = False
            else:
                is_update = True
            # TODO: Validate bookmarks, exclude invalid bookmarks from bulk operations
            _update_bookmark_data(netscape_bookmark, bookmark)
            if is_update:
                bookmarks_to_update.append(bookmark)
            else:
                bookmarks_to_create.append(bookmark)

            result.success = result.success + 1
        except:
            shortened_bookmark_tag_str = str(netscape_bookmark)[:100] + '...'
            logging.exception('Error importing bookmark: ' + shortened_bookmark_tag_str)
            result.failed = result.failed + 1

    # Bulk update bookmarks in DB
    Bookmark.objects.bulk_update(bookmarks_to_update,
                                 ['url', 'date_added', 'date_modified', 'unread', 'title', 'description', 'owner'])
    # Bulk insert new bookmarks into DB
    Bookmark.objects.bulk_create(bookmarks_to_create)

    # Bulk assign tags
    # In Django 3, bulk_create does not return the auto-generated IDs when bulk inserting,
    # so we have to reload the inserted bookmarks, and match them to the parsed bookmarks by URL
    existing_bookmarks = Bookmark.objects.filter(owner=user, url__in=batch_urls)

    BookmarkToTagRelationShip = Bookmark.tags.through
    relationships = []

    for netscape_bookmark in netscape_bookmarks:
        bookmark = next(
            (bookmark for bookmark in existing_bookmarks if bookmark.url == netscape_bookmark.href), None)

        if not bookmark:
            # Something is wrong, we should have just created this bookmark
            shortened_bookmark_tag_str = str(netscape_bookmark)[:100] + '...'
            logging.warning(
                f'Failed to assign tags to the bookmark: {shortened_bookmark_tag_str}. Could not find bookmark by URL.')

        tag_names = parse_tag_string(netscape_bookmark.tag_string)
        tags = tag_cache.get(tag_names)
        for tag in tags:
            relationships.append(BookmarkToTagRelationShip(bookmark=bookmark, tag=tag))

    BookmarkToTagRelationShip.objects.bulk_create(relationships, ignore_conflicts=True)


def _update_bookmark_data(netscape_bookmark: NetscapeBookmark, bookmark: Bookmark):
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
