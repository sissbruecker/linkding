import urllib.parse
from typing import Set, List

from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db import models
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import Bookmark, BookmarkFilters, User, UserProfile, Tag
from bookmarks import utils

DEFAULT_PAGE_SIZE = 30


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

        if profile.bookmark_date_display == UserProfile.BOOKMARK_DATE_DISPLAY_RELATIVE:
            self.display_date = utils.humanize_relative_date(bookmark.date_added)
        elif profile.bookmark_date_display == UserProfile.BOOKMARK_DATE_DISPLAY_ABSOLUTE:
            self.display_date = utils.humanize_absolute_date(bookmark.date_added)

        self.show_notes_button = bookmark.notes and not profile.permanent_notes
        self.show_mark_as_read = is_editable and bookmark.unread
        self.show_unshare = is_editable and bookmark.shared and profile.enable_sharing

        self.has_extra_actions = self.show_notes_button or self.show_mark_as_read or self.show_unshare


class BookmarkListContext:
    def __init__(self, request: WSGIRequest) -> None:
        self.request = request
        self.filters = BookmarkFilters(self.request)

        user = request.user
        user_profile = request.user_profile
        query_set = self.get_bookmark_query_set()
        page_number = request.GET.get('page')
        paginator = Paginator(query_set, DEFAULT_PAGE_SIZE)
        bookmarks_page = paginator.get_page(page_number)
        # Prefetch related objects, this avoids n+1 queries when accessing fields in templates
        models.prefetch_related_objects(bookmarks_page.object_list, 'owner', 'tags')

        self.items = [BookmarkItem(bookmark, user, user_profile) for bookmark in bookmarks_page]

        self.is_empty = paginator.count == 0
        self.bookmarks_page = bookmarks_page
        self.return_url = self.generate_return_url(page_number)
        self.link_target = user_profile.bookmark_link_target
        self.date_display = user_profile.bookmark_date_display
        self.show_url = user_profile.display_url
        self.show_favicons = user_profile.enable_favicons
        self.show_notes = user_profile.permanent_notes

    def generate_return_url(self, page: int):
        base_url = self.get_base_url()
        url_query = {}
        if self.filters.query:
            url_query['q'] = self.filters.query
        if self.filters.user:
            url_query['user'] = self.filters.user
        if page is not None:
            url_query['page'] = page
        url_params = urllib.parse.urlencode(url_query)
        return_url = base_url if url_params == '' else base_url + '?' + url_params
        return urllib.parse.quote_plus(return_url)

    def get_base_url(self):
        raise Exception(f'Must be implemented by subclass')

    def get_bookmark_query_set(self):
        raise Exception(f'Must be implemented by subclass')


class ActiveBookmarkListContext(BookmarkListContext):
    def get_base_url(self):
        return reverse('bookmarks:index')

    def get_bookmark_query_set(self):
        return queries.query_bookmarks(self.request.user,
                                       self.request.user_profile,
                                       self.filters.query)


class ArchivedBookmarkListContext(BookmarkListContext):
    def get_base_url(self):
        return reverse('bookmarks:archived')

    def get_bookmark_query_set(self):
        return queries.query_archived_bookmarks(self.request.user,
                                                self.request.user_profile,
                                                self.filters.query)


class SharedBookmarkListContext(BookmarkListContext):
    def get_base_url(self):
        return reverse('bookmarks:shared')

    def get_bookmark_query_set(self):
        user = User.objects.filter(username=self.filters.user).first()
        public_only = not self.request.user.is_authenticated
        return queries.query_shared_bookmarks(user,
                                              self.request.user_profile,
                                              self.filters.query,
                                              public_only)


class TagGroup:
    def __init__(self, char: str):
        self.tags = []
        self.char = char

    @staticmethod
    def create_tag_groups(tags: Set[Tag]):
        # Ensure groups, as well as tags within groups, are ordered alphabetically
        sorted_tags = sorted(tags, key=lambda x: str.lower(x.name))
        group = None
        groups = []

        # Group tags that start with a different character than the previous one
        for tag in sorted_tags:
            tag_char = tag.name[0].lower()

            if not group or group.char != tag_char:
                group = TagGroup(tag_char)
                groups.append(group)

            group.tags.append(tag)

        return groups


class TagCloudContext:
    def __init__(self, request: WSGIRequest) -> None:
        self.request = request
        self.filters = BookmarkFilters(self.request)

        query_set = self.get_tag_query_set()
        tags = list(query_set)
        selected_tags = self.get_selected_tags(tags)
        unique_tags = utils.unique(tags, key=lambda x: str.lower(x.name))
        unique_selected_tags = utils.unique(selected_tags, key=lambda x: str.lower(x.name))
        has_selected_tags = len(unique_selected_tags) > 0
        unselected_tags = set(unique_tags).symmetric_difference(unique_selected_tags)
        groups = TagGroup.create_tag_groups(unselected_tags)

        self.tags = unique_tags
        self.groups = groups
        self.selected_tags = unique_selected_tags
        self.has_selected_tags = has_selected_tags

    def get_tag_query_set(self):
        raise Exception(f'Must be implemented by subclass')

    def get_selected_tags(self, tags: List[Tag]):
        parsed_query = queries.parse_query_string(self.filters.query)
        tag_names = parsed_query['tag_names']
        if self.request.user_profile.tag_search == UserProfile.TAG_SEARCH_LAX:
            tag_names = tag_names + parsed_query['search_terms']
        tag_names = [tag_name.lower() for tag_name in tag_names]

        return [tag for tag in tags if tag.name.lower() in tag_names]


class ActiveTagCloudContext(TagCloudContext):
    def get_tag_query_set(self):
        return queries.query_bookmark_tags(self.request.user,
                                           self.request.user_profile,
                                           self.filters.query)


class ArchivedTagCloudContext(TagCloudContext):
    def get_tag_query_set(self):
        return queries.query_archived_bookmark_tags(self.request.user,
                                                    self.request.user_profile,
                                                    self.filters.query)


class SharedTagCloudContext(TagCloudContext):
    def get_tag_query_set(self):
        user = User.objects.filter(username=self.filters.user).first()
        public_only = not self.request.user.is_authenticated
        return queries.query_shared_bookmark_tags(user,
                                                  self.request.user_profile,
                                                  self.filters.query,
                                                  public_only)
