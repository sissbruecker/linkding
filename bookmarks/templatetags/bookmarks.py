from typing import List

from django import template

from bookmarks.models import BookmarkForm, BookmarkFilters, Tag, build_tag_string, User

register = template.Library()


@register.inclusion_tag('bookmarks/form.html', name='bookmark_form', takes_context=True)
def bookmark_form(context, form: BookmarkForm, cancel_url: str, bookmark_id: int = 0, auto_close: bool = False):
    return {
        'request': context['request'],
        'form': form,
        'auto_close': auto_close,
        'bookmark_id': bookmark_id,
        'cancel_url': cancel_url
    }


@register.inclusion_tag('bookmarks/search.html', name='bookmark_search', takes_context=True)
def bookmark_search(context, filters: BookmarkFilters, tags: [Tag], mode: str = ''):
    tag_names = [tag.name for tag in tags]
    tags_string = build_tag_string(tag_names, ' ')
    return {
        'request': context['request'],
        'filters': filters,
        'tags_string': tags_string,
        'mode': mode,
    }


@register.inclusion_tag('bookmarks/user_select.html', name='user_select', takes_context=True)
def user_select(context, filters: BookmarkFilters, users: List[User]):
    sorted_users = sorted(users, key=lambda x: str.lower(x.username))
    return {
        'filters': filters,
        'users': sorted_users,
    }
