from typing import List

from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Tag

def get_or_create_tags(tag_names: List[str], user: User):
    return [get_or_create_tag(tag_name, user) for tag_name in tag_names]


def get_or_create_tag(name: str, user: User):
    try:
        return Tag.objects.get(name=name, owner=user)
    except Tag.DoesNotExist:
        tag = Tag(name=name, owner=user)
        tag.date_added = timezone.now()
        tag.save()
        return tag
