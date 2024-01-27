import logging
import operator
from typing import List

from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Tag
from bookmarks.utils import unique

logger = logging.getLogger(__name__)


def get_or_create_tags(tag_names: List[str], user: User):
    tags = [get_or_create_tag(tag_name, user) for tag_name in tag_names]
    return unique(tags, operator.attrgetter("id"))


def get_or_create_tag(name: str, user: User):
    try:
        return Tag.objects.get(name__iexact=name, owner=user)
    except Tag.DoesNotExist:
        tag = Tag(name=name, owner=user)
        tag.date_added = timezone.now()
        tag.save()
        return tag
    except Tag.MultipleObjectsReturned:
        # Legacy databases might contain duplicate tags with different capitalization
        first_tag = Tag.objects.filter(name__iexact=name, owner=user).first()
        message = (
            "Found multiple tags for the name '{0}' with different capitalization. "
            "Using the first tag with the name '{1}'. "
            "Since v.1.2 tags work case-insensitive, which means duplicates of the same name are not allowed anymore. "
            "To solve this error remove the duplicate tag in admin."
        ).format(name, first_tag.name)
        logger.error(message)
        return first_tag
