import requests
from bs4 import BeautifulSoup
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
    bookmark.date_modified = timezone.now()
    bookmark.save()


def update_bookmark(bookmark: Bookmark):
    # Update website info
    _update_website_metadata(bookmark)
    # Update dates
    bookmark.date_modified = timezone.now()
    bookmark.save()


def _update_website_metadata(bookmark: Bookmark):
    # noinspection PyBroadException
    try:
        page_text = load_page(bookmark.url)
        soup = BeautifulSoup(page_text, 'html.parser')

        title = soup.title.string if soup.title is not None else None
        description_tag = soup.find('meta', attrs={'name': 'description'})
        description = description_tag['content'] if description_tag is not None else None

        bookmark.website_title = title
        bookmark.website_description = description
    except Exception:
        bookmark.website_title = None
        bookmark.website_description = None


def load_page(url: str):
    r = requests.get(url)
    return r.text
