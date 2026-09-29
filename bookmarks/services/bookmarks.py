import logging

from django.utils import timezone

from bookmarks.models import Bookmark, User, parse_tag_string
from bookmarks.services import auto_tagging, tasks, website_loader
from bookmarks.services.tags import get_or_create_tags

logger = logging.getLogger(__name__)


def create_bookmark(
    bookmark: Bookmark,
    tag_string: str,
    current_user: User,
    disable_html_snapshot: bool = False,
):
    # If URL is already bookmarked, then update it
    existing_bookmark: Bookmark = Bookmark.query_existing(
        current_user, bookmark.url
    ).first()

    if existing_bookmark is not None:
        _merge_bookmark_data(bookmark, existing_bookmark)
        return update_bookmark(
            existing_bookmark,
            tag_string,
            current_user,
            update_fields=_MERGED_BOOKMARK_FIELDS,
        )

    with tasks.track_bookmark_changes(current_user) as changes:
        # Set currently logged in user as owner
        bookmark.owner = current_user
        # Set dates only if not already provided
        # This allows to sync existing dates through the REST API for example
        if not bookmark.date_added:
            bookmark.date_added = timezone.now()
        if not bookmark.date_modified:
            bookmark.date_modified = timezone.now()
        bookmark.save()
        # Update tag list
        tags = _get_bookmark_tags(bookmark, tag_string, current_user)
        changes.lock_tags(tags)
        bookmark.tags.set(tags)
        bookmark.save()
        changes.track_created(bookmark)

    # Schedule background tasks after the transaction, so that they can load
    # the bookmark
    # Create snapshot on web archive
    tasks.create_web_archive_snapshot(current_user, bookmark, False)
    # Load favicon
    tasks.load_favicon(current_user, bookmark)
    # Load preview image
    tasks.load_preview_image(current_user, bookmark)
    # Create HTML snapshot
    if (
        current_user.profile.enable_automatic_html_snapshots
        and not disable_html_snapshot
    ):
        tasks.create_html_snapshot(bookmark)

    return bookmark


def update_bookmark(
    bookmark: Bookmark,
    tag_string: str | None,
    current_user: User,
    update_fields: list[str] | None = None,
):
    """
    Saves changes to a bookmark. If update_fields is given, only these fields
    are saved, so that changes to other fields that were made since the
    bookmark was loaded are not reverted. If tag_string is None, the existing
    tags are kept, and only tags from auto tagging rules are added.
    """
    # Detect URL change
    original_bookmark = Bookmark.objects.get(id=bookmark.id)
    has_url_changed = original_bookmark.url != bookmark.url

    with tasks.track_bookmark_changes(current_user) as changes:
        if tag_string is None:
            tags = get_or_create_tags(
                _get_auto_tag_names(bookmark, current_user), current_user
            )
        else:
            tags = _get_bookmark_tags(bookmark, tag_string, current_user)
        # Tags must be locked before the bookmark, see lock_tags
        changes.lock_tags(tags)
        changes.track([bookmark.id])
        # Update tag list
        if tag_string is None:
            bookmark.tags.add(*tags)
        else:
            bookmark.tags.set(tags)
        # Update dates
        bookmark.date_modified = timezone.now()
        if update_fields is None:
            bookmark.save()
        else:
            saved_fields = {*update_fields, "date_modified"}
            if "url" in saved_fields:
                saved_fields.add("url_normalized")
            bookmark.save(update_fields=saved_fields)

    # Update favicon
    tasks.load_favicon(current_user, bookmark)
    # Update preview image
    tasks.load_preview_image(current_user, bookmark)

    if has_url_changed:
        # Update web archive snapshot, if URL changed
        tasks.create_web_archive_snapshot(current_user, bookmark, True)

    return bookmark


def enhance_with_website_metadata(bookmark: Bookmark):
    # Fills in missing title and description, without saving the bookmark.
    # Should be called before creating the bookmark, so that the data sent to
    # webhooks includes the website metadata.
    metadata = website_loader.load_website_metadata(bookmark.url)
    if not bookmark.title:
        bookmark.title = metadata.title or ""

    if not bookmark.description:
        bookmark.description = metadata.description or ""


def archive_bookmark(bookmark: Bookmark):
    with tasks.track_bookmark_changes(bookmark.owner, [bookmark.id]):
        bookmark.is_archived = True
        bookmark.date_modified = timezone.now()
        # Only save changed fields, to not revert changes that were made since
        # the bookmark was loaded, for example by background tasks
        bookmark.save(update_fields=["is_archived", "date_modified"])
    return bookmark


def archive_bookmarks(bookmark_ids: [int | str], current_user: User):
    _update_bookmarks(bookmark_ids, current_user, is_archived=True)


def unarchive_bookmark(bookmark: Bookmark):
    with tasks.track_bookmark_changes(bookmark.owner, [bookmark.id]):
        bookmark.is_archived = False
        bookmark.date_modified = timezone.now()
        # See archive_bookmark
        bookmark.save(update_fields=["is_archived", "date_modified"])
    return bookmark


def unarchive_bookmarks(bookmark_ids: [int | str], current_user: User):
    _update_bookmarks(bookmark_ids, current_user, is_archived=False)


def delete_bookmark(bookmark: Bookmark):
    with tasks.track_bookmark_changes(bookmark.owner, [bookmark.id]):
        bookmark.delete()


def delete_bookmarks(bookmark_ids: [int | str], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    with tasks.track_bookmark_changes(current_user, sanitized_bookmark_ids):
        Bookmark.objects.filter(
            owner=current_user, id__in=sanitized_bookmark_ids
        ).delete()


def tag_bookmarks(bookmark_ids: [int | str], tag_string: str, current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    owned_bookmark_ids = Bookmark.objects.filter(
        owner=current_user, id__in=sanitized_bookmark_ids
    ).values_list("id", flat=True)
    tag_names = parse_tag_string(tag_string)

    with tasks.track_bookmark_changes(current_user) as changes:
        tags = get_or_create_tags(tag_names, current_user)
        # Tags must be locked before the bookmarks, see lock_tags
        changes.lock_tags(tags)
        changes.track(sanitized_bookmark_ids)

        BookmarkToTagRelationShip = Bookmark.tags.through
        relationships = []
        for tag in tags:
            for bookmark_id in owned_bookmark_ids:
                relationships.append(
                    BookmarkToTagRelationShip(bookmark_id=bookmark_id, tag=tag)
                )

        # Insert all bookmark -> tag associations at once, should ignore errors if association already exists
        BookmarkToTagRelationShip.objects.bulk_create(
            relationships, ignore_conflicts=True
        )
        Bookmark.objects.filter(id__in=owned_bookmark_ids).update(
            date_modified=timezone.now()
        )


def untag_bookmarks(bookmark_ids: [int | str], tag_string: str, current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    owned_bookmark_ids = Bookmark.objects.filter(
        owner=current_user, id__in=sanitized_bookmark_ids
    ).values_list("id", flat=True)
    tag_names = parse_tag_string(tag_string)

    with tasks.track_bookmark_changes(current_user, sanitized_bookmark_ids):
        tags = get_or_create_tags(tag_names, current_user)

        BookmarkToTagRelationShip = Bookmark.tags.through
        for tag in tags:
            # Remove all bookmark -> tag associations for the owned bookmarks and the current tag
            BookmarkToTagRelationShip.objects.filter(
                bookmark_id__in=owned_bookmark_ids, tag=tag
            ).delete()

        Bookmark.objects.filter(id__in=owned_bookmark_ids).update(
            date_modified=timezone.now()
        )


def mark_bookmarks_as_read(bookmark_ids: [int | str], current_user: User):
    _update_bookmarks(bookmark_ids, current_user, unread=False)


def mark_bookmarks_as_unread(bookmark_ids: [int | str], current_user: User):
    _update_bookmarks(bookmark_ids, current_user, unread=True)


def share_bookmarks(bookmark_ids: [int | str], current_user: User):
    _update_bookmarks(bookmark_ids, current_user, shared=True)


def unshare_bookmarks(bookmark_ids: [int | str], current_user: User):
    _update_bookmarks(bookmark_ids, current_user, shared=False)


def _update_bookmarks(bookmark_ids: [int | str], current_user: User, **fields):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    with tasks.track_bookmark_changes(current_user, sanitized_bookmark_ids):
        Bookmark.objects.filter(
            owner=current_user, id__in=sanitized_bookmark_ids
        ).update(**fields, date_modified=timezone.now())


def refresh_bookmarks_metadata(bookmark_ids: [int | str], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    owned_bookmarks = Bookmark.objects.filter(
        owner=current_user, id__in=sanitized_bookmark_ids
    )

    for bookmark in owned_bookmarks:
        tasks.refresh_metadata(bookmark)
        tasks.load_preview_image(current_user, bookmark)


def create_html_snapshots(bookmark_ids: list[int | str], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    owned_bookmarks = Bookmark.objects.filter(
        owner=current_user, id__in=sanitized_bookmark_ids
    )

    tasks.create_html_snapshots(owned_bookmarks)


# Fields that are copied when adding a bookmark for an existing URL
_MERGED_BOOKMARK_FIELDS = ["title", "description", "notes", "unread", "shared"]


def _merge_bookmark_data(from_bookmark: Bookmark, to_bookmark: Bookmark):
    to_bookmark.title = from_bookmark.title
    to_bookmark.description = from_bookmark.description
    to_bookmark.notes = from_bookmark.notes
    to_bookmark.unread = from_bookmark.unread
    to_bookmark.shared = from_bookmark.shared


def _get_bookmark_tags(bookmark: Bookmark, tag_string: str, user: User):
    tag_names = parse_tag_string(tag_string)

    for auto_tag_name in _get_auto_tag_names(bookmark, user):
        if auto_tag_name not in tag_names:
            tag_names.append(auto_tag_name)

    return get_or_create_tags(tag_names, user)


def _get_auto_tag_names(bookmark: Bookmark, user: User) -> list[str]:
    if not user.profile.auto_tagging_rules:
        return []
    try:
        return list(
            auto_tagging.get_tags(user.profile.auto_tagging_rules, bookmark.url)
        )
    except Exception as e:
        logger.error(
            f"Failed to auto-tag bookmark. url={bookmark.url}",
            exc_info=e,
        )
        return []


def _sanitize_id_list(bookmark_ids: [int | str]) -> [int]:
    # Convert string ids to int if necessary
    return [int(bm_id) if isinstance(bm_id, str) else bm_id for bm_id in bookmark_ids]
