from typing import List

from django import template

from bookmarks.models import BookmarkForm, Tag

register = template.Library()


@register.inclusion_tag('bookmarks/form.html', name='bookmark_form')
def bookmark_form(form: BookmarkForm):
    return {
        'form': form,
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
