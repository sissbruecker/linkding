from typing import List

from django import template

from bookmarks.models import (
    BookmarkSearch,
    BookmarkSearchForm,
    User,
)

register = template.Library()


@register.inclusion_tag(
    "bookmarks/search.html", name="bookmark_search", takes_context=True
)
def bookmark_search(context, search: BookmarkSearch, mode: str = ""):
    search_form = BookmarkSearchForm(search, editable_fields=["q"])

    if mode == "shared":
        preferences_form = BookmarkSearchForm(search, editable_fields=["sort"])
    else:
        preferences_form = BookmarkSearchForm(
            search, editable_fields=["sort", "shared", "unread"]
        )
    return {
        "request": context["request"],
        "search": search,
        "search_form": search_form,
        "preferences_form": preferences_form,
        "mode": mode,
    }


@register.inclusion_tag(
    "bookmarks/user_select.html", name="user_select", takes_context=True
)
def user_select(context, search: BookmarkSearch, users: List[User]):
    sorted_users = sorted(users, key=lambda x: str.lower(x.username))
    form = BookmarkSearchForm(search, editable_fields=["user"], users=sorted_users)
    return {
        "search": search,
        "users": sorted_users,
        "form": form,
    }
