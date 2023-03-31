from typing import Optional

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet
from django.utils import timezone

from bookmarks.models import Bookmark, Tag
from bookmarks.utils import unique


def query_bookmarks(user: User, query_string: str, query_dates: Optional[dict[str, str]]=None) -> QuerySet:
    return _base_bookmarks_query(user, query_string, query_dates) \
        .filter(is_archived=False)


def query_archived_bookmarks(user: User, query_string: str, query_dates: Optional[dict[str, str]]=None) -> QuerySet:
    return _base_bookmarks_query(user, query_string, query_dates) \
        .filter(is_archived=True)


def query_shared_bookmarks(user: Optional[User], query_string: str, query_dates: Optional[dict[str, str]]=None) -> QuerySet:
    return _base_bookmarks_query(user, query_string, query_dates) \
        .filter(shared=True) \
        .filter(owner__profile__enable_sharing=True)


def _base_bookmarks_query(user: Optional[User], query_string: str, query_dates: Optional[dict[str, str]]=None) -> QuerySet:
    query_set = Bookmark.objects
    if not query_dates:
        query_dates = {}

    # Filter for user
    if user:
        query_set = query_set.filter(owner=user)

    # Split query into search terms and tags
    query = parse_query_string(query_string)

    # Filter for search terms and tags
    for term in query['search_terms']:
        query_set = query_set.filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(website_title__icontains=term)
            | Q(website_description__icontains=term)
            | Q(url__icontains=term)
        )

    for tag_name in query['tag_names']:
        query_set = query_set.filter(
            tags__name__iexact=tag_name
        )

    # Untagged bookmarks
    if query['untagged']:
        query_set = query_set.filter(
            tags=None
        )
    # Unread bookmarks
    if query['unread']:
        query_set = query_set.filter(
            unread=True
        )

    # Ensure dates are converted to correct `datetime` representation
    dates = parse_query_dates(query_dates)

    # Filter by dates
    date_filters = {
        'since_added': 'date_added__gte',
        'until_added': 'date_added__lte',
        'since_modified': 'date_modified__gte',
        'until_modified': 'date_modified__lte'
    }

    for field_name, comparison_operator in date_filters.items():
        if dates.get(field_name):
            query = {
                comparison_operator: query_dates[field_name]
            }
            query_set = query_set.filter(**query)

    # Sort by date added
    query_set = query_set.order_by('-date_added')

    return query_set


def query_bookmark_tags(user: User, query_string: str) -> QuerySet:
    bookmarks_query = query_bookmarks(user, query_string)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_archived_bookmark_tags(user: User, query_string: str) -> QuerySet:
    bookmarks_query = query_archived_bookmarks(user, query_string)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_shared_bookmark_tags(user: Optional[User], query_string: str) -> QuerySet:
    bookmarks_query = query_shared_bookmarks(user, query_string)

    query_set = Tag.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def query_shared_bookmark_users(query_string: str) -> QuerySet:
    bookmarks_query = query_shared_bookmarks(None, query_string)

    query_set = User.objects.filter(bookmark__in=bookmarks_query)

    return query_set.distinct()


def get_user_tags(user: User):
    return Tag.objects.filter(owner=user).all()


def parse_query_string(query_string):
    # Sanitize query params
    if not query_string:
        query_string = ''

    # Split query into search terms and tags
    keywords = query_string.strip().split(' ')
    keywords = [word for word in keywords if word]

    search_terms = [word for word in keywords if word[0] != '#' and word[0] != '!']
    tag_names = [word[1:] for word in keywords if word[0] == '#']
    tag_names = unique(tag_names, str.lower)

    # Special search commands
    untagged = '!untagged' in keywords
    unread = '!unread' in keywords

    return {
        'search_terms': search_terms,
        'tag_names': tag_names,
        'untagged': untagged,
        'unread': unread,
    }


def parse_query_dates(query_dates: dict[str, str]):
    # Convert timestamps, dropping any invalid formatted dates
    format_patterns = ["%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]
    dates = {}
    for query_date, value in query_dates.items():
        for pattern in format_patterns:
            try:
                dates[query_date] = timezone.datetime.strptime(value, pattern)
            except:
                pass
    return dates