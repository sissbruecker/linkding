from typing import Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet, Exists, OuterRef, Case, When, CharField
from django.db.models.expressions import RawSQL
from django.db.models.functions import Lower

from bookmarks.models import (
    Bookmark,
    BookmarkBundle,
    BookmarkSearch,
    Tag,
    UserProfile,
    parse_tag_string,
)
from bookmarks.utils import unique


def query_bookmarks(
    user: User,
    profile: UserProfile,
    search: BookmarkSearch,
) -> QuerySet:
    return _base_bookmarks_query(user, profile, search).filter(is_archived=False)


def query_archived_bookmarks(
    user: User, profile: UserProfile, search: BookmarkSearch
) -> QuerySet:
    return _base_bookmarks_query(user, profile, search).filter(is_archived=True)


def query_shared_bookmarks(
    user: Optional[User],
    profile: UserProfile,
    search: BookmarkSearch,
    public_only: bool,
) -> QuerySet:
    conditions = Q(shared=True) & Q(owner__profile__enable_sharing=True)
    if public_only:
        conditions = conditions & Q(owner__profile__enable_public_sharing=True)

    return _base_bookmarks_query(user, profile, search).filter(conditions)


def _filter_bundle(query_set: QuerySet, bundle: BookmarkBundle) -> QuerySet:
    # Search terms
    search_terms = parse_query_string(bundle.search)["search_terms"]
    for term in search_terms:
        conditions = (
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(notes__icontains=term)
            | Q(url__icontains=term)
        )
        query_set = query_set.filter(conditions)

    # Any tags - at least one tag must match
    any_tags = parse_tag_string(bundle.any_tags, " ")
    if len(any_tags) > 0:
        tag_conditions = Q()
        for tag in any_tags:
            tag_conditions |= Q(tags__name__iexact=tag)

        query_set = query_set.filter(
            Exists(Bookmark.objects.filter(tag_conditions, id=OuterRef("id")))
        )

    # All tags - all tags must match
    all_tags = parse_tag_string(bundle.all_tags, " ")
    for tag in all_tags:
        query_set = query_set.filter(tags__name__iexact=tag)

    # Excluded tags - no tags must match
    exclude_tags = parse_tag_string(bundle.excluded_tags, " ")
    if len(exclude_tags) > 0:
        tag_conditions = Q()
        for tag in exclude_tags:
            tag_conditions |= Q(tags__name__iexact=tag)
        query_set = query_set.exclude(
            Exists(Bookmark.objects.filter(tag_conditions, id=OuterRef("id")))
        )

    return query_set


def _base_bookmarks_query(
    user: Optional[User],
    profile: UserProfile,
    search: BookmarkSearch,
) -> QuerySet:
    query_set = Bookmark.objects

    # Filter for user
    if user:
        query_set = query_set.filter(owner=user)

    # Filter by modified_since if provided
    if search.modified_since:
        try:
            query_set = query_set.filter(date_modified__gt=search.modified_since)
        except ValidationError:
            # If the date format is invalid, ignore the filter
            pass

    # Filter by added_since if provided
    if search.added_since:
        try:
            query_set = query_set.filter(date_added__gt=search.added_since)
        except ValidationError:
            # If the date format is invalid, ignore the filter
            pass

    # Split query into search terms and tags
    query = parse_query_string(search.q)

    # Filter for search terms and tags
    for term in query["search_terms"]:
        conditions = (
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(notes__icontains=term)
            | Q(url__icontains=term)
        )

        if profile.tag_search == UserProfile.TAG_SEARCH_LAX:
            conditions = conditions | Exists(
                Bookmark.objects.filter(id=OuterRef("id"), tags__name__iexact=term)
            )

        query_set = query_set.filter(conditions)

    for tag_name in query["tag_names"]:
        query_set = query_set.filter(tags__name__iexact=tag_name)

    # Untagged bookmarks
    if query["untagged"]:
        query_set = query_set.filter(tags=None)
    # Legacy unread bookmarks filter from query
    if query["unread"]:
        query_set = query_set.filter(unread=True)

    # Unread filter from bookmark search
    if search.unread == BookmarkSearch.FILTER_UNREAD_YES:
        query_set = query_set.filter(unread=True)
    elif search.unread == BookmarkSearch.FILTER_UNREAD_NO:
        query_set = query_set.filter(unread=False)

    # Shared filter
    if search.shared == BookmarkSearch.FILTER_SHARED_SHARED:
        query_set = query_set.filter(shared=True)
    elif search.shared == BookmarkSearch.FILTER_SHARED_UNSHARED:
        query_set = query_set.filter(shared=False)

    # Filter by bundle
    if search.bundle:
        query_set = _filter_bundle(query_set, search.bundle)

    # Sort
    if (
        search.sort == BookmarkSearch.SORT_TITLE_ASC
        or search.sort == BookmarkSearch.SORT_TITLE_DESC
    ):
        # For the title, the resolved_title logic from the Bookmark entity needs
        # to be replicated as there is no corresponding database field
        query_set = query_set.annotate(
            effective_title=Case(
                When(Q(title__isnull=False) & ~Q(title__exact=""), then=Lower("title")),
                default=Lower("url"),
                output_field=CharField(),
            )
        )

        # For SQLite, if the ICU extension is loaded, use the custom collation
        # loaded into the connection. This results in an improved sort order for
        # unicode characters (umlauts, etc.)
        if settings.USE_SQLITE and settings.USE_SQLITE_ICU_EXTENSION:
            order_field = RawSQL("effective_title COLLATE ICU", ())
        else:
            order_field = "effective_title"

        if search.sort == BookmarkSearch.SORT_TITLE_ASC:
            query_set = query_set.order_by(order_field)
        elif search.sort == BookmarkSearch.SORT_TITLE_DESC:
            query_set = query_set.order_by(order_field).reverse()
    elif search.sort == BookmarkSearch.SORT_ADDED_ASC:
        query_set = query_set.order_by("date_added")
    elif search.sort == BookmarkSearch.SORT_USAGE_DESC:
        # Sort by access count descending, then by date added descending
        query_set = query_set.order_by("-access_count", "-date_added")
    else:
        # Sort by date added, descending by default
        query_set = query_set.order_by("-date_added")

    return query_set


def query_bookmark_tags(
    user: User, profile: UserProfile, search: BookmarkSearch
) -> QuerySet:
    bookmarks_query = query_bookmarks(user, profile, search)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_archived_bookmark_tags(
    user: User, profile: UserProfile, search: BookmarkSearch
) -> QuerySet:
    bookmarks_query = query_archived_bookmarks(user, profile, search)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_shared_bookmark_tags(
    user: Optional[User],
    profile: UserProfile,
    search: BookmarkSearch,
    public_only: bool,
) -> QuerySet:
    bookmarks_query = query_shared_bookmarks(user, profile, search, public_only)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_shared_bookmark_users(
    profile: UserProfile, search: BookmarkSearch, public_only: bool
) -> QuerySet:
    bookmarks_query = query_shared_bookmarks(None, profile, search, public_only)

    query_set = User.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def get_user_tags(user: User):
    return Tag.objects.filter(owner=user).all()


def parse_query_string(query_string):
    # Sanitize query params
    if not query_string:
        query_string = ""

    # Split query into search terms and tags
    keywords = query_string.strip().split(" ")
    keywords = [word for word in keywords if word]

    search_terms = [word for word in keywords if word[0] != "#" and word[0] != "!"]
    tag_names = [word[1:] for word in keywords if word[0] == "#"]
    tag_names = unique(tag_names, str.lower)

    # Special search commands
    untagged = "!untagged" in keywords
    unread = "!unread" in keywords

    return {
        "search_terms": search_terms,
        "tag_names": tag_names,
        "untagged": untagged,
        "unread": unread,
    }
