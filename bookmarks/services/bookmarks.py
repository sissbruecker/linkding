import requests
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark, BookmarkForm, parse_tag_string
from services.tags import get_or_create_tags


def create_bookmark(form: BookmarkForm, current_user: User):
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


def _update_bookmark_tags(bookmark: Bookmark, tag_string: str, user: User):
    tag_names = parse_tag_string(tag_string, ' ')
    tags = get_or_create_tags(tag_names, user)
    bookmark.tags.set(tags)


def load_page(url: str):
    r = requests.get(url)
    return r.text
