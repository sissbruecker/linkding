from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark


def create_bookmark(bookmark: Bookmark, current_user: User):
    # Update website info
    _update_website_metadata(bookmark)
    # Set currently logged in user as owner
    bookmark.owner = current_user
    # Set dates
    bookmark.date_added = timezone.now()
    bookmark.save()


def _update_website_metadata(bookmark: Bookmark):
    # TODO: Load website metadata
    bookmark.website_title = 'Title from website'
    bookmark.website_description = 'Description from website'
    pass
