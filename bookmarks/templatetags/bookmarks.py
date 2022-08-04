from typing import List

from django import template
from django.core.paginator import Page

from bookmarks.models import BookmarkForm, BookmarkFilters, Tag, build_tag_string, User
from bookmarks.utils import unique

register = template.Library()


@register.inclusion_tag('bookmarks/form.html', name='bookmark_form')
def bookmark_form(form: BookmarkForm, cancel_url: str, bookmark_id: int = 0, auto_close: bool = False):
    return {
        'form': form,
        'auto_close': auto_close,
        'bookmark_id': bookmark_id,
        'cancel_url': cancel_url
    }


class TagGroup:
    def __init__(self, char):
        self.tags = []
        self.char = char


def create_tag_groups(tags: List[Tag]):
    # Only display each tag name once, ignoring casing
    # This covers cases where the tag cloud contains shared tags with duplicate names
    # Also means that the cloud can not make assumptions that it will necessarily contain
    # all tags of the current user
    unique_tags = unique(tags, key=lambda x: str.lower(x.name))
    # Ensure groups, as well as tags within groups, are ordered alphabetically
    sorted_tags = sorted(unique_tags, key=lambda x: str.lower(x.name))
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


@register.inclusion_tag('bookmarks/tag_cloud.html', name='tag_cloud', takes_context=True)
def tag_cloud(context, tags: List[Tag]):
    groups = create_tag_groups(tags)
    return {
        'groups': groups,
    }


@register.inclusion_tag('bookmarks/bookmark_list.html', name='bookmark_list', takes_context=True)
def bookmark_list(context, bookmarks: Page, return_url: str, link_target: str = '_blank'):
    return {
        'request': context['request'],
        'bookmarks': bookmarks,
        'return_url': return_url,
        'link_target': link_target,
    }


@register.inclusion_tag('bookmarks/search.html', name='bookmark_search', takes_context=True)
def bookmark_search(context, filters: BookmarkFilters, tags: [Tag], mode: str = ''):
    tag_names = [tag.name for tag in tags]
    tags_string = build_tag_string(tag_names, ' ')
    return {
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
