import logging
import operator

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from bookmarks.models import Bookmark, Tag
from bookmarks.utils import unique

logger = logging.getLogger(__name__)


def get_or_create_tags(tag_names: list[str], user: User):
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
            f"Found multiple tags for the name '{name}' with different capitalization. "
            f"Using the first tag with the name '{first_tag.name}'. "
            "Since v.1.2 tags work case-insensitive, which means duplicates of the same name are not allowed anymore. "
            "To solve this error remove the duplicate tag in admin."
        )
        logger.error(message)
        return first_tag


def merge_tags(target_tag: Tag, merge_tags: list[Tag]):
    with transaction.atomic():
        BookmarkTag = Bookmark.tags.through

        # Get all bookmarks that have any of the merge tags, but do not
        # already have the target tag
        bookmark_ids = list(
            Bookmark.objects.filter(tags__in=merge_tags)
            .exclude(tags=target_tag)
            .values_list("id", flat=True)
            .distinct()
        )

        # Create new relationships to the target tag
        new_relationships = [
            BookmarkTag(tag_id=target_tag.id, bookmark_id=bookmark_id)
            for bookmark_id in bookmark_ids
        ]

        if new_relationships:
            BookmarkTag.objects.bulk_create(new_relationships)

        # Bulk delete all relationships for merge tags
        merge_tag_ids = [tag.id for tag in merge_tags]
        BookmarkTag.objects.filter(tag_id__in=merge_tag_ids).delete()

        # Delete the merged tags
        Tag.objects.filter(id__in=merge_tag_ids).delete()
