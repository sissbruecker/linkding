from collections.abc import Iterable
import logging
import operator

from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone

from bookmarks.models import Bookmark, Tag
from bookmarks.utils import unique

logger = logging.getLogger(__name__)

_MAX_RELATED_TAGS = 5

def get_or_create_tags(tag_names: list[str], user: User):
    tags = [get_or_create_tag(tag_name, user) for tag_name in tag_names]
    return unique(tags, operator.attrgetter("id"))


def get_or_create_tag(name: str, user: User, description: str = ""):
    try:
        return Tag.objects.get(name__iexact=name, owner=user)
    except Tag.DoesNotExist:
        tag = Tag(name=name, owner=user)
        tag.description = description
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


def get_related_tags(tag: Tag, user: User) -> Iterable[Tag]:
    """
    Returns up to _MAX_RELATED_TAGS tags that are most often applied with the given tag.
    """

    # Get all bookmarks with the same tag as the lookup tag.
    # This will get inlined as a subquery.
    bookmarks = Bookmark.objects.filter(tags=tag, owner=user)

    tags = (
        Tag
            .objects
            # Get tags applied to all bookmarks from the previous step owned by the current user
            # We're hoping the cost of a second join is outweighed by the speed-up gained by being able to
            # use the index on bookmark.owner_id to prune out the users who do not own the tag.
            .filter(bookmark__id__in=bookmarks, bookmark__owner=user)
            # Ignore the tag we're currently looking up
            .exclude(id=tag.id)
            # Apply a GROUP BY tag id and count up the amount of times the same tag shows up
            .annotate(Count("id"))
            # Sort by that count descending and get the first _MAX_RELATED_TAGS tags.
            .order_by("-id__count")
            [:_MAX_RELATED_TAGS]
    )

    return tags
