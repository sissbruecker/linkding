import urllib.parse
from typing import Set, List
import re

from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db import models
from django.urls import reverse

from bookmarks import queries
from bookmarks import utils
from bookmarks.models import (
    Bookmark,
    BookmarkSearch,
    User,
    UserProfile,
    Tag,
)

DEFAULT_PAGE_SIZE = 30
CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


class BookmarkItem:
    def __init__(self, bookmark: Bookmark, user: User, profile: UserProfile) -> None:
        self.bookmark = bookmark

        is_editable = bookmark.owner == user
        self.is_editable = is_editable

        self.id = bookmark.id
        self.url = bookmark.url
        self.title = bookmark.resolved_title
        self.description = bookmark.resolved_description
        self.notes = bookmark.notes
        self.tag_names = bookmark.tag_names
        self.web_archive_snapshot_url = bookmark.web_archive_snapshot_url
        self.favicon_file = bookmark.favicon_file
        self.is_archived = bookmark.is_archived
        self.unread = bookmark.unread
        self.owner = bookmark.owner

        css_classes = []
        if bookmark.unread:
            css_classes.append("unread")
        if bookmark.shared:
            css_classes.append("shared")

        self.css_classes = " ".join(css_classes)

        if profile.bookmark_date_display == UserProfile.BOOKMARK_DATE_DISPLAY_RELATIVE:
            self.display_date = utils.humanize_relative_date(bookmark.date_added)
        elif (
            profile.bookmark_date_display == UserProfile.BOOKMARK_DATE_DISPLAY_ABSOLUTE
        ):
            self.display_date = utils.humanize_absolute_date(bookmark.date_added)

        self.show_notes_button = bookmark.notes and not profile.permanent_notes
        self.show_mark_as_read = is_editable and bookmark.unread
        self.show_unshare = is_editable and bookmark.shared and profile.enable_sharing

        self.has_extra_actions = (
            self.show_notes_button or self.show_mark_as_read or self.show_unshare
        )


class BookmarkListContext:
    def __init__(self, request: WSGIRequest) -> None:
        user = request.user
        user_profile = request.user_profile

        self.request = request
        self.search = BookmarkSearch.from_request(
            self.request.GET, user_profile.search_preferences
        )

        query_set = self.get_bookmark_query_set()
        page_number = request.GET.get("page")
        paginator = Paginator(query_set, DEFAULT_PAGE_SIZE)
        bookmarks_page = paginator.get_page(page_number)
        # Prefetch related objects, this avoids n+1 queries when accessing fields in templates
        models.prefetch_related_objects(bookmarks_page.object_list, "owner", "tags")

        self.items = [
            BookmarkItem(bookmark, user, user_profile) for bookmark in bookmarks_page
        ]

        self.is_empty = paginator.count == 0
        self.bookmarks_page = bookmarks_page
        self.bookmarks_total = paginator.count
        self.return_url = self.generate_return_url(
            self.search, self.get_base_url(), page_number
        )
        self.action_url = self.generate_action_url(
            self.search, self.get_base_action_url(), self.return_url
        )
        self.link_target = user_profile.bookmark_link_target
        self.date_display = user_profile.bookmark_date_display
        self.description_display = user_profile.bookmark_description_display
        self.description_max_lines = user_profile.bookmark_description_max_lines
        self.show_url = user_profile.display_url
        self.show_favicons = user_profile.enable_favicons
        self.show_notes = user_profile.permanent_notes

    @staticmethod
    def generate_return_url(search: BookmarkSearch, base_url: str, page: int = None):
        query_params = search.query_params
        if page is not None:
            query_params["page"] = page
        query_string = urllib.parse.urlencode(query_params)

        return base_url if query_string == "" else base_url + "?" + query_string

    @staticmethod
    def generate_action_url(
        search: BookmarkSearch, base_action_url: str, return_url: str
    ):
        query_params = search.query_params
        query_params["return_url"] = return_url
        query_string = urllib.parse.urlencode(query_params)

        return (
            base_action_url
            if query_string == ""
            else base_action_url + "?" + query_string
        )

    def get_base_url(self):
        raise Exception("Must be implemented by subclass")

    def get_base_action_url(self):
        raise Exception("Must be implemented by subclass")

    def get_bookmark_query_set(self):
        raise Exception("Must be implemented by subclass")


class ActiveBookmarkListContext(BookmarkListContext):
    def get_base_url(self):
        return reverse("bookmarks:index")

    def get_base_action_url(self):
        return reverse("bookmarks:index.action")

    def get_bookmark_query_set(self):
        return queries.query_bookmarks(
            self.request.user, self.request.user_profile, self.search
        )


class ArchivedBookmarkListContext(BookmarkListContext):
    def get_base_url(self):
        return reverse("bookmarks:archived")

    def get_base_action_url(self):
        return reverse("bookmarks:archived.action")

    def get_bookmark_query_set(self):
        return queries.query_archived_bookmarks(
            self.request.user, self.request.user_profile, self.search
        )


class SharedBookmarkListContext(BookmarkListContext):
    def get_base_url(self):
        return reverse("bookmarks:shared")

    def get_base_action_url(self):
        return reverse("bookmarks:shared.action")

    def get_bookmark_query_set(self):
        user = User.objects.filter(username=self.search.user).first()
        public_only = not self.request.user.is_authenticated
        return queries.query_shared_bookmarks(
            user, self.request.user_profile, self.search, public_only
        )


class TagGroup:
    def __init__(self, char: str):
        self.tags = []
        self.char = char

    def __repr__(self):
        return f"<{self.char} TagGroup>"

    @staticmethod
    def create_tag_groups(tags: Set[Tag]):
        # Ensure groups, as well as tags within groups, are ordered alphabetically
        sorted_tags = sorted(tags, key=lambda x: str.lower(x.name))
        group = None
        groups = []
        cjk_used = False
        cjk_group = TagGroup("Ideographic")

        # Group tags that start with a different character than the previous one
        for tag in sorted_tags:
            tag_char = tag.name[0].lower()
            if CJK_RE.match(tag_char):
                cjk_used = True
                cjk_group.tags.append(tag)
            elif not group or group.char != tag_char:
                group = TagGroup(tag_char)
                groups.append(group)
                group.tags.append(tag)
            else:
                group.tags.append(tag)

        if cjk_used:
            groups.append(cjk_group)
        return groups


class TagCloudContext:
    def __init__(self, request: WSGIRequest) -> None:
        user_profile = request.user_profile

        self.request = request
        self.search = BookmarkSearch.from_request(
            self.request.GET, user_profile.search_preferences
        )

        query_set = self.get_tag_query_set()
        tags = list(query_set)
        selected_tags = self.get_selected_tags(tags)
        unique_tags = utils.unique(tags, key=lambda x: str.lower(x.name))
        unique_selected_tags = utils.unique(
            selected_tags, key=lambda x: str.lower(x.name)
        )
        has_selected_tags = len(unique_selected_tags) > 0
        unselected_tags = set(unique_tags).symmetric_difference(unique_selected_tags)
        groups = TagGroup.create_tag_groups(unselected_tags)

        self.tags = unique_tags
        self.groups = groups
        self.selected_tags = unique_selected_tags
        self.has_selected_tags = has_selected_tags

    def get_tag_query_set(self):
        raise Exception("Must be implemented by subclass")

    def get_selected_tags(self, tags: List[Tag]):
        parsed_query = queries.parse_query_string(self.search.q)
        tag_names = parsed_query["tag_names"]
        if self.request.user_profile.tag_search == UserProfile.TAG_SEARCH_LAX:
            tag_names = tag_names + parsed_query["search_terms"]
        tag_names = [tag_name.lower() for tag_name in tag_names]

        return [tag for tag in tags if tag.name.lower() in tag_names]


class ActiveTagCloudContext(TagCloudContext):
    def get_tag_query_set(self):
        return queries.query_bookmark_tags(
            self.request.user, self.request.user_profile, self.search
        )


class ArchivedTagCloudContext(TagCloudContext):
    def get_tag_query_set(self):
        return queries.query_archived_bookmark_tags(
            self.request.user, self.request.user_profile, self.search
        )


class SharedTagCloudContext(TagCloudContext):
    def get_tag_query_set(self):
        user = User.objects.filter(username=self.search.user).first()
        public_only = not self.request.user.is_authenticated
        return queries.query_shared_bookmark_tags(
            user, self.request.user_profile, self.search, public_only
        )
