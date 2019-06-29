from django.contrib.auth.models import User
from django.db.models import Q

from bookmarks.models import Bookmark


def query_bookmarks(user: User, query_string: str):
    query_set = Bookmark.objects

    # Sanitize query params
    if not query_string:
        query_string = ''

    # Filter for user
    query_set = query_set.filter(owner=user)

    # Split query into keywords
    keywords = query_string.strip().split(' ')
    keywords = [word for word in keywords if word]

    # Filter for each keyword
    for word in keywords:
        query_set = query_set.filter(
            Q(title__contains=word)
            | Q(description__contains=word)
            | Q(website_title__contains=word)
            | Q(website_description__contains=word)
        )

    # Sort by modification date
    query_set = query_set.order_by('-date_modified')

    return query_set
