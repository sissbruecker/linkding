import contextlib

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, Exists, OuterRef, Q, QuerySet, When
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
from bookmarks.services.search_query_parser import (
    AndExpression,
    NotExpression,
    OrExpression,
    SearchExpression,
    SearchQueryParseError,
    SpecialKeywordExpression,
    TagExpression,
    TermExpression,
    extract_tag_names_from_query,
    parse_search_query,
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
    user: User | None,
    profile: UserProfile,
    search: BookmarkSearch,
    public_only: bool,
) -> QuerySet:
    conditions = Q(shared=True) & Q(owner__profile__enable_sharing=True)
    if public_only:
        conditions = conditions & Q(owner__profile__enable_public_sharing=True)

    return _base_bookmarks_query(user, profile, search).filter(conditions)


def _convert_ast_to_q_object(ast_node: SearchExpression, profile: UserProfile) -> Q:
    if isinstance(ast_node, TermExpression):
        # Search across title, description, notes, URL
        conditions = (
            Q(title__icontains=ast_node.term)
            | Q(description__icontains=ast_node.term)
            | Q(notes__icontains=ast_node.term)
            | Q(url__icontains=ast_node.term)
        )

        # In lax mode, also search in tag names
        if profile.tag_search == UserProfile.TAG_SEARCH_LAX:
            conditions = conditions | Exists(
                Bookmark.objects.filter(
                    id=OuterRef("id"), tags__name__iexact=ast_node.term
                )
            )

        return conditions

    elif isinstance(ast_node, TagExpression):
        # Use Exists() to avoid reusing the same join when combining multiple tag expressions with and
        return Q(
            Exists(
                Bookmark.objects.filter(
                    id=OuterRef("id"), tags__name__iexact=ast_node.tag
                )
            )
        )

    elif isinstance(ast_node, SpecialKeywordExpression):
        # Handle special keywords
        if ast_node.keyword.lower() == "unread":
            return Q(unread=True)
        elif ast_node.keyword.lower() == "untagged":
            return Q(tags=None)
        else:
            # Unknown keyword, return empty Q object (matches all)
            return Q()

    elif isinstance(ast_node, AndExpression):
        # Combine left and right with AND
        left_q = _convert_ast_to_q_object(ast_node.left, profile)
        right_q = _convert_ast_to_q_object(ast_node.right, profile)
        return left_q & right_q

    elif isinstance(ast_node, OrExpression):
        # Combine left and right with OR
        left_q = _convert_ast_to_q_object(ast_node.left, profile)
        right_q = _convert_ast_to_q_object(ast_node.right, profile)
        return left_q | right_q

    elif isinstance(ast_node, NotExpression):
        # Negate the operand
        operand_q = _convert_ast_to_q_object(ast_node.operand, profile)
        return ~operand_q

    else:
        # Fallback for unknown node types
        return Q()


def _filter_search_query(
    query_set: QuerySet, query_string: str, profile: UserProfile
) -> QuerySet:
    """New search filtering logic using logical expressions."""

    try:
        ast = parse_search_query(query_string)
        if ast:
            search_query = _convert_ast_to_q_object(ast, profile)
            query_set = query_set.filter(search_query)
    except SearchQueryParseError:
        # If the query cannot be parsed, return zero results
        return query_set.none()

    return query_set


def _filter_search_query_legacy(
    query_set: QuerySet, query_string: str, profile: UserProfile
) -> QuerySet:
    """Legacy search filtering logic where everything is just combined with AND."""

    # Split query into search terms and tags
    query = parse_query_string(query_string)

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

    return query_set


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
    user: User | None,
    profile: UserProfile,
    search: BookmarkSearch,
) -> QuerySet:
    query_set = Bookmark.objects

    # Filter for user
    if user:
        query_set = query_set.filter(owner=user)

    # Filter by modified_since if provided
    if search.modified_since:
        # If the date format is invalid, ignore the filter
        with contextlib.suppress(ValidationError):
            query_set = query_set.filter(date_modified__gt=search.modified_since)

    # Filter by added_since if provided
    if search.added_since:
        # If the date format is invalid, ignore the filter
        with contextlib.suppress(ValidationError):
            query_set = query_set.filter(date_added__gt=search.added_since)

    # Filter by search query
    if profile.legacy_search:
        query_set = _filter_search_query_legacy(query_set, search.q, profile)
    else:
        query_set = _filter_search_query(query_set, search.q, profile)

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
    user: User | None,
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


def get_tags_for_query(user: User, profile: UserProfile, query: str) -> QuerySet:
    tag_names = extract_tag_names_from_query(query, profile)

    if not tag_names:
        return Tag.objects.none()

    tag_conditions = Q()
    for tag_name in tag_names:
        tag_conditions |= Q(name__iexact=tag_name)

    return Tag.objects.filter(owner=user).filter(tag_conditions).distinct()


def get_shared_tags_for_query(
    user: User | None, profile: UserProfile, query: str, public_only: bool
) -> QuerySet:
    tag_names = extract_tag_names_from_query(query, profile)

    if not tag_names:
        return Tag.objects.none()

    # Build conditions similar to query_shared_bookmarks
    conditions = Q(bookmark__shared=True) & Q(
        bookmark__owner__profile__enable_sharing=True
    )
    if public_only:
        conditions = conditions & Q(
            bookmark__owner__profile__enable_public_sharing=True
        )
    if user is not None:
        conditions = conditions & Q(bookmark__owner=user)

    tag_conditions = Q()
    for tag_name in tag_names:
        tag_conditions |= Q(name__iexact=tag_name)

    return Tag.objects.filter(conditions).filter(tag_conditions).distinct()


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
