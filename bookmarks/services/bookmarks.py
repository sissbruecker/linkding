from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark, BookmarkForm, parse_tag_string
from bookmarks.services.tags import get_or_create_tags
from bookmarks.services.website_loader import load_website_metadata


def create_bookmark(form: BookmarkForm, current_user: User):
    # If URL is already bookmarked, then update it
    existing_bookmark = Bookmark.objects.filter(owner=current_user, url=form.data['url']).first()

    if existing_bookmark is not None:
        update_form = BookmarkForm(data=form.data, instance=existing_bookmark)
        update_bookmark(update_form, current_user)
        return

    bookmark = form.save(commit=False)
    # Update website info
    _update_website_metadata(bookmark)
    # Set currently logged in user as owner
    bookmark.owner = current_user
    # Set dates
    bookmark.date_added = timezone.now()
    bookmark.date_modified = timezone.now()
    bookmark.save()
    # Update tag list
    _update_bookmark_tags(bookmark, form.data['tag_string'], current_user)
    bookmark.save()


def update_bookmark(form: BookmarkForm, current_user: User):
    bookmark = form.save(commit=False)
    # Update website info
    _update_website_metadata(bookmark)
    # Update tag list
    _update_bookmark_tags(bookmark, form.data['tag_string'], current_user)
    # Update dates
    bookmark.date_modified = timezone.now()
    bookmark.save()


def _update_website_metadata(bookmark: Bookmark):
    metadata = load_website_metadata(bookmark.url)
    bookmark.website_title = metadata.title
    bookmark.website_description = metadata.description


def _update_bookmark_tags(bookmark: Bookmark, tag_string: str, user: User):
    tag_names = parse_tag_string(tag_string, ' ')
    tags = get_or_create_tags(tag_names, user)
    bookmark.tags.set(tags)
