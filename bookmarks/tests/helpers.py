import random
import logging
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.test import APITestCase

from bookmarks.models import Bookmark, BookmarkAsset, Tag


class BookmarkFactoryMixin:
    user = None

    def get_or_create_test_user(self):
        if self.user is None:
            self.user = User.objects.create_user(
                "testuser", "test@example.com", "password123"
            )

        return self.user

    def setup_bookmark(
        self,
        is_archived: bool = False,
        unread: bool = False,
        shared: bool = False,
        tags=None,
        user: User = None,
        url: str = "",
        title: str = None,
        description: str = "",
        notes: str = "",
        website_title: str = "",
        website_description: str = "",
        web_archive_snapshot_url: str = "",
        favicon_file: str = "",
        added: datetime = None,
    ):
        if title is None:
            title = get_random_string(length=32)
        if tags is None:
            tags = []
        if user is None:
            user = self.get_or_create_test_user()
        if not url:
            unique_id = get_random_string(length=32)
            url = "https://example.com/" + unique_id
        if added is None:
            added = timezone.now()
        bookmark = Bookmark(
            url=url,
            title=title,
            description=description,
            notes=notes,
            website_title=website_title,
            website_description=website_description,
            date_added=added,
            date_modified=timezone.now(),
            owner=user,
            is_archived=is_archived,
            unread=unread,
            shared=shared,
            web_archive_snapshot_url=web_archive_snapshot_url,
            favicon_file=favicon_file,
        )
        bookmark.save()
        for tag in tags:
            bookmark.tags.add(tag)
        bookmark.save()
        return bookmark

    def setup_numbered_bookmarks(
        self,
        count: int,
        prefix: str = "",
        suffix: str = "",
        tag_prefix: str = "",
        archived: bool = False,
        unread: bool = False,
        shared: bool = False,
        with_tags: bool = False,
        with_web_archive_snapshot_url: bool = False,
        user: User = None,
    ):
        user = user or self.get_or_create_test_user()
        bookmarks = []

        if not prefix:
            if archived:
                prefix = "Archived Bookmark"
            elif shared:
                prefix = "Shared Bookmark"
            else:
                prefix = "Bookmark"

        if not tag_prefix:
            if archived:
                tag_prefix = "Archived Tag"
            elif shared:
                tag_prefix = "Shared Tag"
            else:
                tag_prefix = "Tag"

        for i in range(1, count + 1):
            title = f"{prefix} {i}{suffix}"
            url = f"https://example.com/{prefix}/{i}"
            tags = []
            if with_tags:
                tag_name = f"{tag_prefix} {i}{suffix}"
                tags = [self.setup_tag(name=tag_name, user=user)]
            web_archive_snapshot_url = ""
            if with_web_archive_snapshot_url:
                web_archive_snapshot_url = f"https://web.archive.org/web/{i}"
            bookmark = self.setup_bookmark(
                url=url,
                title=title,
                is_archived=archived,
                unread=unread,
                shared=shared,
                tags=tags,
                web_archive_snapshot_url=web_archive_snapshot_url,
                user=user,
            )
            bookmarks.append(bookmark)

        return bookmarks

    def get_numbered_bookmark(self, title: str):
        return Bookmark.objects.get(title=title)

    def setup_asset(
        self,
        bookmark: Bookmark,
        date_created: datetime = None,
        file: str = None,
        file_size: int = None,
        asset_type: str = BookmarkAsset.TYPE_SNAPSHOT,
        content_type: str = "image/html",
        display_name: str = None,
        status: str = BookmarkAsset.STATUS_COMPLETE,
        gzip: bool = False,
    ):
        if date_created is None:
            date_created = timezone.now()
        if not file:
            file = get_random_string(length=32)
        if not display_name:
            display_name = file
        asset = BookmarkAsset(
            bookmark=bookmark,
            date_created=date_created,
            file=file,
            file_size=file_size,
            asset_type=asset_type,
            content_type=content_type,
            display_name=display_name,
            status=status,
            gzip=gzip,
        )
        asset.save()
        return asset

    def setup_tag(self, user: User = None, name: str = ""):
        if user is None:
            user = self.get_or_create_test_user()
        if not name:
            name = get_random_string(length=32)
        tag = Tag(name=name, date_added=timezone.now(), owner=user)
        tag.save()
        return tag

    def setup_user(
        self,
        name: str = None,
        enable_sharing: bool = False,
        enable_public_sharing: bool = False,
    ):
        if not name:
            name = get_random_string(length=32)
        user = User.objects.create_user(name, "user@example.com", "password123")
        user.profile.enable_sharing = enable_sharing
        user.profile.enable_public_sharing = enable_public_sharing
        user.profile.save()
        return user

    def get_tags_from_bookmarks(self, bookmarks: [Bookmark]):
        all_tags = []
        for bookmark in bookmarks:
            all_tags = all_tags + list(bookmark.tags.all())
        return all_tags

    def get_random_string(self, length: int = 32):
        return get_random_string(length=length)


class HtmlTestMixin:
    def make_soup(self, html: str):
        return BeautifulSoup(html, features="html.parser")


class LinkdingApiTestCase(APITestCase):
    def get(self, url, expected_status_code=status.HTTP_200_OK):
        response = self.client.get(url)
        self.assertEqual(response.status_code, expected_status_code)
        return response

    def post(self, url, data=None, expected_status_code=status.HTTP_200_OK):
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, expected_status_code)
        return response

    def put(self, url, data=None, expected_status_code=status.HTTP_200_OK):
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, expected_status_code)
        return response

    def patch(self, url, data=None, expected_status_code=status.HTTP_200_OK):
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, expected_status_code)
        return response

    def delete(self, url, expected_status_code=status.HTTP_200_OK):
        response = self.client.delete(url)
        self.assertEqual(response.status_code, expected_status_code)
        return response


class BookmarkHtmlTag:
    def __init__(
        self,
        href: str = "",
        title: str = "",
        description: str = "",
        add_date: str = "",
        tags: str = "",
        to_read: bool = False,
        private: bool = True,
    ):
        self.href = href
        self.title = title
        self.description = description
        self.add_date = add_date
        self.tags = tags
        self.to_read = to_read
        self.private = private


class ImportTestMixin:
    def render_tag(self, tag: BookmarkHtmlTag):
        return f"""
        <DT>
        <A {f'HREF="{tag.href}"' if tag.href else ''}
           {f'ADD_DATE="{tag.add_date}"' if tag.add_date else ''}
           {f'TAGS="{tag.tags}"' if tag.tags else ''}
           TOREAD="{1 if tag.to_read else 0}"
           PRIVATE="{1 if tag.private else 0}">
           {tag.title if tag.title else ''}
        </A>
        {f'<DD>{tag.description}' if tag.description else ''}
        """

    def render_html(self, tags: List[BookmarkHtmlTag] = None, tags_html: str = ""):
        if tags:
            rendered_tags = [self.render_tag(tag) for tag in tags]
            tags_html = "\n".join(rendered_tags)
        return f"""
        <!DOCTYPE NETSCAPE-Bookmark-file-1>
        <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
        <TITLE>Bookmarks</TITLE>
        <H1>Bookmarks</H1>
        <DL><p>
        {tags_html}
        </DL><p>
        """


_words = [
    "quasi",
    "consequatur",
    "necessitatibus",
    "debitis",
    "quod",
    "vero",
    "qui",
    "commodi",
    "quod",
    "odio",
    "aliquam",
    "veniam",
    "architecto",
    "consequatur",
    "autem",
    "qui",
    "iste",
    "asperiores",
    "soluta",
    "et",
]


def random_sentence(num_words: int = None, including_word: str = ""):
    if num_words is None:
        num_words = random.randint(5, 10)
    selected_words = random.choices(_words, k=num_words)
    if including_word:
        selected_words.append(including_word)
    random.shuffle(selected_words)

    return " ".join(selected_words)


def disable_logging(f):
    def wrapper(*args):
        logging.disable(logging.CRITICAL)
        result = f(*args)
        logging.disable(logging.NOTSET)

        return result

    return wrapper


def collapse_whitespace(text: str):
    text = text.replace("\n", "").replace("\r", "")
    return " ".join(text.split())
