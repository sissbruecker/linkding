import re
import urllib.parse
from typing import Set, List

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db import models
from django.http import Http404
from django.urls import reverse

from bookmarks import queries
from bookmarks import utils
from bookmarks.models import (
    Bookmark,
    BookmarkAsset,
    BookmarkSearch,
    User,
    UserProfile,
    Tag,
)
from bookmarks.services.wayback import generate_fallback_webarchive_url

CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


class RequestContext:
    index_view = "bookmarks:index"
    action_view = "bookmarks:index.action"

    def __init__(self, request: WSGIRequest):
        self.request = request
        self.index_url = reverse(self.index_view)
        self.action_url = reverse(self.action_view)
        self.query_params = request.GET.copy()
        self.query_params.pop("details", None)

    def get_url(self, view_url: str, add: dict = None, remove: dict = None) -> str:
        query_params = self.query_params.copy()
        if add:
            query_params.update(add)
        if remove:
            for key in remove:
                query_params.pop(key, None)
        encoded_params = query_params.urlencode()
        return view_url + "?" + encoded_params if encoded_params else view_url

    def index(self, add: dict = None, remove: dict = None) -> str:
        return self.get_url(self.index_url, add=add, remove=remove)

    def action(self, add: dict = None, remove: dict = None) -> str:
        return self.get_url(self.action_url, add=add, remove=remove)

    def details(self, bookmark_id: int) -> str:
        return self.get_url(self.index_url, add={"details": bookmark_id})

    def get_bookmark_query_set(self, search: BookmarkSearch):
        raise NotImplementedError("Must be implemented by subclass")

    def get_tag_query_set(self, search: BookmarkSearch):
        raise NotImplementedError("Must be implemented by subclass")


class ActiveBookmarksContext(RequestContext):
    index_view = "bookmarks:index"
    action_view = "bookmarks:index.action"

    def get_bookmark_query_set(self, search: BookmarkSearch):
        return queries.query_bookmarks(
            self.request.user, self.request.user_profile, search
        )

    def get_tag_query_set(self, search: BookmarkSearch):
        return queries.query_bookmark_tags(
            self.request.user, self.request.user_profile, search
        )


class ArchivedBookmarksContext(RequestContext):
    index_view = "bookmarks:archived"
    action_view = "bookmarks:archived.action"

    def get_bookmark_query_set(self, search: BookmarkSearch):
        return queries.query_archived_bookmarks(
            self.request.user, self.request.user_profile, search
        )

    def get_tag_query_set(self, search: BookmarkSearch):
        return queries.query_archived_bookmark_tags(
            self.request.user, self.request.user_profile, search
        )


class SharedBookmarksContext(RequestContext):
    index_view = "bookmarks:shared"
    action_view = "bookmarks:shared.action"

    def get_bookmark_query_set(self, search: BookmarkSearch):
        user = User.objects.filter(username=search.user).first()
        public_only = not self.request.user.is_authenticated
        return queries.query_shared_bookmarks(
            user, self.request.user_profile, search, public_only
        )

    def get_tag_query_set(self, search: BookmarkSearch):
        user = User.objects.filter(username=search.user).first()
        public_only = not self.request.user.is_authenticated
        return queries.query_shared_bookmark_tags(
            user, self.request.user_profile, search, public_only
        )


class BookmarkItem:
    def __init__(
        self,
        context: RequestContext,
        bookmark: Bookmark,
        user: User,
        profile: UserProfile,
    ) -> None:
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
        if not self.web_archive_snapshot_url:
            self.web_archive_snapshot_url = generate_fallback_webarchive_url(
                bookmark.url, bookmark.date_added
            )
        self.favicon_file = bookmark.favicon_file
        self.preview_image_file = bookmark.preview_image_file
        self.is_archived = bookmark.is_archived
        self.unread = bookmark.unread
        self.owner = bookmark.owner
        self.details_url = context.details(bookmark.id)

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
    request_context = RequestContext

    def __init__(self, request: WSGIRequest) -> None:
        request_context = self.request_context(request)
        user = request.user
        user_profile = request.user_profile

        self.request = request
        self.search = BookmarkSearch.from_request(
            self.request.GET, user_profile.search_preferences
        )

        query_set = request_context.get_bookmark_query_set(self.search)
        page_number = request.GET.get("page")
        paginator = Paginator(query_set, user_profile.items_per_page)
        bookmarks_page = paginator.get_page(page_number)
        # Prefetch related objects, this avoids n+1 queries when accessing fields in templates
        models.prefetch_related_objects(bookmarks_page.object_list, "owner", "tags")

        self.items = [
            BookmarkItem(request_context, bookmark, user, user_profile)
            for bookmark in bookmarks_page
        ]
        self.is_empty = paginator.count == 0
        self.bookmarks_page = bookmarks_page
        self.bookmarks_total = paginator.count

        self.return_url = request_context.index()
        self.action_url = request_context.action()

        self.link_target = user_profile.bookmark_link_target
        self.date_display = user_profile.bookmark_date_display
        self.description_display = user_profile.bookmark_description_display
        self.description_max_lines = user_profile.bookmark_description_max_lines
        self.show_url = user_profile.display_url
        self.show_view_action = user_profile.display_view_bookmark_action
        self.show_edit_action = user_profile.display_edit_bookmark_action
        self.show_archive_action = user_profile.display_archive_bookmark_action
        self.show_remove_action = user_profile.display_remove_bookmark_action
        self.show_favicons = user_profile.enable_favicons
        self.show_preview_images = user_profile.enable_preview_images
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


class ActiveBookmarkListContext(BookmarkListContext):
    request_context = ActiveBookmarksContext


class ArchivedBookmarkListContext(BookmarkListContext):
    request_context = ArchivedBookmarksContext


class SharedBookmarkListContext(BookmarkListContext):
    request_context = SharedBookmarksContext


class TagGroup:
    def __init__(self, char: str):
        self.tags = []
        self.char = char

    def __repr__(self):
        return f"<{self.char} TagGroup>"

    @staticmethod
    def create_tag_groups(mode: str, tags: Set[Tag]):
        if mode == UserProfile.TAG_GROUPING_ALPHABETICAL:
            return TagGroup._create_tag_groups_alphabetical(tags)
        elif mode == UserProfile.TAG_GROUPING_DISABLED:
            return TagGroup._create_tag_groups_disabled(tags)
        else:
            raise ValueError(f"{mode} is not a valid tag grouping mode")

    @staticmethod
    def _create_tag_groups_alphabetical(tags: Set[Tag]):
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

    @staticmethod
    def _create_tag_groups_disabled(tags: Set[Tag]):
        if len(tags) == 0:
            return []

        sorted_tags = sorted(tags, key=lambda x: str.lower(x.name))
        group = TagGroup("Ungrouped")
        for tag in sorted_tags:
            group.tags.append(tag)

        return [group]


class TagCloudContext:
    request_context = RequestContext

    def __init__(self, request: WSGIRequest) -> None:
        request_context = self.request_context(request)
        user_profile = request.user_profile

        self.request = request
        self.search = BookmarkSearch.from_request(
            self.request.GET, user_profile.search_preferences
        )

        query_set = request_context.get_tag_query_set(self.search)
        tags = list(query_set)
        selected_tags = self.get_selected_tags(tags)
        unique_tags = utils.unique(tags, key=lambda x: str.lower(x.name))
        unique_selected_tags = utils.unique(
            selected_tags, key=lambda x: str.lower(x.name)
        )
        has_selected_tags = len(unique_selected_tags) > 0
        unselected_tags = set(unique_tags).symmetric_difference(unique_selected_tags)
        groups = TagGroup.create_tag_groups(user_profile.tag_grouping, unselected_tags)

        self.tags = unique_tags
        self.groups = groups
        self.selected_tags = unique_selected_tags
        self.has_selected_tags = has_selected_tags

    def get_selected_tags(self, tags: List[Tag]):
        parsed_query = queries.parse_query_string(self.search.q)
        tag_names = parsed_query["tag_names"]
        if self.request.user_profile.tag_search == UserProfile.TAG_SEARCH_LAX:
            tag_names = tag_names + parsed_query["search_terms"]
        tag_names = [tag_name.lower() for tag_name in tag_names]

        return [tag for tag in tags if tag.name.lower() in tag_names]


class ActiveTagCloudContext(TagCloudContext):
    request_context = ActiveBookmarksContext


class ArchivedTagCloudContext(TagCloudContext):
    request_context = ArchivedBookmarksContext


class SharedTagCloudContext(TagCloudContext):
    request_context = SharedBookmarksContext


class BookmarkAssetItem:
    def __init__(self, asset: BookmarkAsset):
        self.asset = asset

        self.id = asset.id
        self.display_name = asset.display_name
        self.asset_type = asset.asset_type
        self.content_type = asset.content_type
        self.file = asset.file
        self.file_size = asset.file_size
        self.status = asset.status

        icon_classes = []
        text_classes = []
        if asset.status == BookmarkAsset.STATUS_PENDING:
            icon_classes.append("text-tertiary")
            text_classes.append("text-tertiary")
        elif asset.status == BookmarkAsset.STATUS_FAILURE:
            icon_classes.append("text-error")
            text_classes.append("text-error")
        else:
            icon_classes.append("icon-color")

        self.icon_classes = " ".join(icon_classes)
        self.text_classes = " ".join(text_classes)


class BookmarkDetailsContext:
    request_context = RequestContext

    def __init__(self, request: WSGIRequest, bookmark: Bookmark):
        request_context = self.request_context(request)

        user = request.user
        user_profile = request.user_profile

        self.edit_return_url = request_context.details(bookmark.id)
        self.action_url = request_context.action(add={"details": bookmark.id})
        self.delete_url = request_context.action()
        self.close_url = request_context.index()

        self.bookmark = bookmark
        self.profile = request.user_profile
        self.is_editable = bookmark.owner == user
        self.sharing_enabled = user_profile.enable_sharing
        self.preview_image_enabled = user_profile.enable_preview_images
        self.show_link_icons = user_profile.enable_favicons and bookmark.favicon_file
        # For now hide files section if snapshots are not supported
        self.show_files = settings.LD_ENABLE_SNAPSHOTS

        self.web_archive_snapshot_url = bookmark.web_archive_snapshot_url
        if not self.web_archive_snapshot_url:
            self.web_archive_snapshot_url = generate_fallback_webarchive_url(
                bookmark.url, bookmark.date_added
            )

        self.assets = [
            BookmarkAssetItem(asset) for asset in bookmark.bookmarkasset_set.all()
        ]
        self.has_pending_assets = any(
            asset.status == BookmarkAsset.STATUS_PENDING for asset in self.assets
        )
        self.latest_snapshot = next(
            (
                asset
                for asset in self.assets
                if asset.asset.asset_type == BookmarkAsset.TYPE_SNAPSHOT
                and asset.status == BookmarkAsset.STATUS_COMPLETE
            ),
            None,
        )


class ActiveBookmarkDetailsContext(BookmarkDetailsContext):
    request_context = ActiveBookmarksContext


class ArchivedBookmarkDetailsContext(BookmarkDetailsContext):
    request_context = ArchivedBookmarksContext


class SharedBookmarkDetailsContext(BookmarkDetailsContext):
    request_context = SharedBookmarksContext


def get_details_context(
    request: WSGIRequest, context_type
) -> BookmarkDetailsContext | None:
    bookmark_id = request.GET.get("details")
    if not bookmark_id:
        return None

    try:
        bookmark = Bookmark.objects.get(pk=int(bookmark_id))
    except Bookmark.DoesNotExist:
        # just ignore, might end up in a situation where the bookmark was deleted
        # in between navigating back and forth
        return None

    is_owner = bookmark.owner == request.user
    is_shared = (
        request.user.is_authenticated
        and bookmark.shared
        and bookmark.owner.profile.enable_sharing
    )
    is_public_shared = bookmark.shared and bookmark.owner.profile.enable_public_sharing
    if not is_owner and not is_shared and not is_public_shared:
        raise Http404("Bookmark does not exist")
    if request.method == "POST" and not is_owner:
        raise Http404("Bookmark does not exist")

    return context_type(request, bookmark)
