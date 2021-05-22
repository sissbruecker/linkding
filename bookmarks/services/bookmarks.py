from typing import Union

from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark, parse_tag_string
from bookmarks.services.tags import get_or_create_tags
from bookmarks.services.website_loader import load_website_metadata
from bookmarks.services import tasks


def create_bookmark(bookmark: Bookmark, tag_string: str, current_user: User):
    # If URL is already bookmarked, then update it
    existing_bookmark: Bookmark = Bookmark.objects.filter(owner=current_user, url=bookmark.url).first()

    if existing_bookmark is not None:
        _merge_bookmark_data(bookmark, existing_bookmark)
        return update_bookmark(existing_bookmark, tag_string, current_user)

    # Update website info
    _update_website_metadata(bookmark)
    # Set currently logged in user as owner
    bookmark.owner = current_user
    # Set dates
    bookmark.date_added = timezone.now()
    bookmark.date_modified = timezone.now()
    bookmark.save()
    # Update tag list
    _update_bookmark_tags(bookmark, tag_string, current_user)
    bookmark.save()
    # Create snapshot on web archive
    tasks.create_web_archive_snapshot(bookmark.id)

    return bookmark


def update_bookmark(bookmark: Bookmark, tag_string, current_user: User):
    # Detect URL change
    original_bookmark = Bookmark.objects.get(id=bookmark.id)
    has_url_changed = original_bookmark.url != bookmark.url
    # Update website info
    _update_website_metadata(bookmark)
    # Update tag list
    _update_bookmark_tags(bookmark, tag_string, current_user)
    # Update dates
    bookmark.date_modified = timezone.now()
    bookmark.save()
    # Update web archive snapshot, if URL changed
    if has_url_changed:
        tasks.create_web_archive_snapshot(bookmark.id)

    return bookmark


def archive_bookmark(bookmark: Bookmark):
    bookmark.is_archived = True
    bookmark.date_modified = timezone.now()
    bookmark.save()
    return bookmark


def archive_bookmarks(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    bookmarks = Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids)

    bookmarks.update(is_archived=True, date_modified=timezone.now())


def unarchive_bookmark(bookmark: Bookmark):
    bookmark.is_archived = False
    bookmark.date_modified = timezone.now()
    bookmark.save()
    return bookmark


def unarchive_bookmarks(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    bookmarks = Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids)

    bookmarks.update(is_archived=False, date_modified=timezone.now())


def delete_bookmarks(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    bookmarks = Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids)

    bookmarks.delete()


def tag_bookmarks(bookmark_ids: [Union[int, str]], tag_string: str, current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    bookmarks = Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids)
    tag_names = parse_tag_string(tag_string, ' ')
    tags = get_or_create_tags(tag_names, current_user)

    for bookmark in bookmarks:
        bookmark.tags.add(*tags)
        bookmark.date_modified = timezone.now()

    Bookmark.objects.bulk_update(bookmarks, ['date_modified'])


def untag_bookmarks(bookmark_ids: [Union[int, str]], tag_string: str, current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    bookmarks = Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids)
    tag_names = parse_tag_string(tag_string, ' ')
    tags = get_or_create_tags(tag_names, current_user)

    for bookmark in bookmarks:
        bookmark.tags.remove(*tags)
        bookmark.date_modified = timezone.now()

    Bookmark.objects.bulk_update(bookmarks, ['date_modified'])


def _merge_bookmark_data(from_bookmark: Bookmark, to_bookmark: Bookmark):
    to_bookmark.title = from_bookmark.title
    to_bookmark.description = from_bookmark.description


def _update_website_metadata(bookmark: Bookmark):
    metadata = load_website_metadata(bookmark.url)
    bookmark.website_title = metadata.title
    bookmark.website_description = metadata.description


def _update_bookmark_tags(bookmark: Bookmark, tag_string: str, user: User):
    tag_names = parse_tag_string(tag_string, ' ')
    tags = get_or_create_tags(tag_names, user)
    bookmark.tags.set(tags)


def _sanitize_id_list(bookmark_ids: [Union[int, str]]) -> [int]:
    # Convert string ids to int if necessary
    return [int(bm_id) if isinstance(bm_id, str) else bm_id for bm_id in bookmark_ids]
