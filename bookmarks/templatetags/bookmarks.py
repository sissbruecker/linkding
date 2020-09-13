from typing import List

from django import template
from django.core.paginator import Page

from bookmarks.models import BookmarkForm, Tag, build_tag_string

register = template.Library()


@register.inclusion_tag('bookmarks/form.html', name='bookmark_form')
def bookmark_form(form: BookmarkForm, all_tags: List[Tag], cancel_url: str, bookmark_id: int = 0, auto_close: bool = False):

    all_tag_names = [tag.name for tag in all_tags]
    all_tags_string = build_tag_string(all_tag_names, ' ')

    return {
        'form': form,
        'auto_close': auto_close,
        'all_tags': all_tags_string,
        'bookmark_id': bookmark_id,
        'cancel_url': cancel_url
    }


class TagGroup:
    def __init__(self, char):
        self.tags = []
        self.char = char


def create_tag_groups(tags: List[Tag]):
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


@register.inclusion_tag('bookmarks/tag_cloud.html', name='tag_cloud', takes_context=True)
def tag_cloud(context, tags: List[Tag]):
    groups = create_tag_groups(tags)
    return {
        'groups': groups,
    }


@register.inclusion_tag('bookmarks/bookmark_list.html', name='bookmark_list', takes_context=True)
def bookmark_list(context, bookmarks: Page, return_url: str):
    return {
        'bookmarks': bookmarks,
        'return_url': return_url
    }
