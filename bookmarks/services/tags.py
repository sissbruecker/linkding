import operator
from typing import List

from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Tag
from bookmarks.utils import unique


def get_or_create_tags(tag_names: List[str], user: User):
    tags = [get_or_create_tag(tag_name, user) for tag_name in tag_names]
    return unique(tags, operator.attrgetter('id'))


def get_or_create_tag(name: str, user: User):
    try:
        return Tag.objects.get(name__iexact=name, owner=user)
    except Tag.DoesNotExist:
        tag = Tag(name=name, owner=user)
        tag.date_added = timezone.now()
        tag.save()
        return tag
