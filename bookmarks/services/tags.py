import contextlib
import logging
import operator

from django.contrib.auth.models import User
from django.utils import timezone

from bookmarks.models import Bookmark, Tag
from bookmarks.services import tasks
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


@contextlib.contextmanager
def track_tag_changes(tags: list[Tag]):
    """
    Tracks changes to all bookmarks that have any of the tags, for sending
    webhook events when renaming, merging or deleting tags. Tags can belong to
    different users. See tasks.track_bookmark_changes.
    """
    tags = list(tags)
    owners = User.objects.filter(id__in={tag.owner_id for tag in tags}).order_by("id")
    with contextlib.ExitStack() as stack:
        for owner in owners:
            changes = stack.enter_context(tasks.track_bookmark_changes(owner))
            if not changes.enabled:
                continue
            owner_tag_ids = [tag.id for tag in tags if tag.owner_id == owner.id]
            # Lock the tags before resolving their bookmarks. Adding or removing
            # the tags concurrently then either completes before, so that the
            # bookmark is tracked, or waits until this change is complete.
            list(
                Tag.objects.filter(id__in=owner_tag_ids)
                .order_by("id")
                .select_for_update()
            )
            changes.track(
                Bookmark.objects.filter(owner=owner, tags__id__in=owner_tag_ids)
                .values_list("id", flat=True)
                .distinct()
            )
        yield


def delete_tag(tag: Tag):
    # Deleting a tag removes it from all of its bookmarks
    with track_tag_changes([tag]):
        tag.delete()
