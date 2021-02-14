from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark, parse_tag_string
from bookmarks.services.tags import get_or_create_tags
from bookmarks.services.website_loader import load_website_metadata


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
    return bookmark


def update_bookmark(bookmark: Bookmark, tag_string, current_user: User):
    # Update website info
    _update_website_metadata(bookmark)
    # Update tag list
    _update_bookmark_tags(bookmark, tag_string, current_user)
    # Update dates
    bookmark.date_modified = timezone.now()
    bookmark.save()
    return bookmark


def archive_bookmark(bookmark: Bookmark):
    bookmark.is_archived = True
    bookmark.save()
    return bookmark


def unarchive_bookmark(bookmark: Bookmark):
    bookmark.is_archived = False
    bookmark.save()
    return bookmark


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
