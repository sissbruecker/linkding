import logging
import os
from typing import Union

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from bookmarks.models import Bookmark, BookmarkAsset, parse_tag_string
from bookmarks.services import tasks
from bookmarks.services import website_loader
from bookmarks.services import auto_tagging
from bookmarks.services.tags import get_or_create_tags

logger = logging.getLogger(__name__)


def create_bookmark(bookmark: Bookmark, tag_string: str, current_user: User):
    # If URL is already bookmarked, then update it
    existing_bookmark: Bookmark = Bookmark.objects.filter(
        owner=current_user, url=bookmark.url
    ).first()

    if existing_bookmark is not None:
        _merge_bookmark_data(bookmark, existing_bookmark)
        return update_bookmark(existing_bookmark, tag_string, current_user)

    # Set currently logged in user as owner
    bookmark.owner = current_user
    # Set dates
    bookmark.date_added = timezone.now()
    bookmark.date_modified = timezone.now()
    bookmark.save()
    # Update tag list
    _update_bookmark_tags(bookmark, tag_string, current_user)
    bookmark.save()
    # Create snapshot on web archive
    tasks.create_web_archive_snapshot(current_user, bookmark, False)
    # Load favicon
    tasks.load_favicon(current_user, bookmark)
    # Load preview image
    tasks.load_preview_image(current_user, bookmark)
    # Create HTML snapshot
    if current_user.profile.enable_automatic_html_snapshots:
        tasks.create_html_snapshot(bookmark)

    return bookmark


def update_bookmark(bookmark: Bookmark, tag_string, current_user: User):
    # Detect URL change
    original_bookmark = Bookmark.objects.get(id=bookmark.id)
    has_url_changed = original_bookmark.url != bookmark.url
    # Update tag list
    _update_bookmark_tags(bookmark, tag_string, current_user)
    # Update dates
    bookmark.date_modified = timezone.now()
    bookmark.save()
    # Update favicon
    tasks.load_favicon(current_user, bookmark)
    # Update preview image
    tasks.load_preview_image(current_user, bookmark)

    if has_url_changed:
        # Update web archive snapshot, if URL changed
        tasks.create_web_archive_snapshot(current_user, bookmark, True)

    return bookmark


def enhance_with_website_metadata(bookmark: Bookmark):
    metadata = website_loader.load_website_metadata(bookmark.url)
    if not bookmark.title:
        bookmark.title = metadata.title or ""

    if not bookmark.description:
        bookmark.description = metadata.description or ""

    bookmark.save()


def archive_bookmark(bookmark: Bookmark):
    bookmark.is_archived = True
    bookmark.date_modified = timezone.now()
    bookmark.save()
    return bookmark


def archive_bookmarks(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids).update(
        is_archived=True, date_modified=timezone.now()
    )


def unarchive_bookmark(bookmark: Bookmark):
    bookmark.is_archived = False
    bookmark.date_modified = timezone.now()
    bookmark.save()
    return bookmark


def unarchive_bookmarks(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids).update(
        is_archived=False, date_modified=timezone.now()
    )


def delete_bookmarks(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids).delete()


def tag_bookmarks(bookmark_ids: [Union[int, str]], tag_string: str, current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    owned_bookmark_ids = Bookmark.objects.filter(
        owner=current_user, id__in=sanitized_bookmark_ids
    ).values_list("id", flat=True)
    tag_names = parse_tag_string(tag_string)
    tags = get_or_create_tags(tag_names, current_user)

    BookmarkToTagRelationShip = Bookmark.tags.through
    relationships = []
    for tag in tags:
        for bookmark_id in owned_bookmark_ids:
            relationships.append(
                BookmarkToTagRelationShip(bookmark_id=bookmark_id, tag=tag)
            )

    # Insert all bookmark -> tag associations at once, should ignore errors if association already exists
    BookmarkToTagRelationShip.objects.bulk_create(relationships, ignore_conflicts=True)
    Bookmark.objects.filter(id__in=owned_bookmark_ids).update(
        date_modified=timezone.now()
    )


def untag_bookmarks(
    bookmark_ids: [Union[int, str]], tag_string: str, current_user: User
):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)
    owned_bookmark_ids = Bookmark.objects.filter(
        owner=current_user, id__in=sanitized_bookmark_ids
    ).values_list("id", flat=True)
    tag_names = parse_tag_string(tag_string)
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


def mark_bookmarks_as_read(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids).update(
        unread=False, date_modified=timezone.now()
    )


def mark_bookmarks_as_unread(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids).update(
        unread=True, date_modified=timezone.now()
    )


def share_bookmarks(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids).update(
        shared=True, date_modified=timezone.now()
    )


def unshare_bookmarks(bookmark_ids: [Union[int, str]], current_user: User):
    sanitized_bookmark_ids = _sanitize_id_list(bookmark_ids)

    Bookmark.objects.filter(owner=current_user, id__in=sanitized_bookmark_ids).update(
        shared=False, date_modified=timezone.now()
    )


def _generate_upload_asset_filename(asset: BookmarkAsset, filename: str):
    formatted_datetime = asset.date_created.strftime("%Y-%m-%d_%H%M%S")
    return f"{asset.asset_type}_{formatted_datetime}_{filename}"


def upload_asset(bookmark: Bookmark, upload_file: UploadedFile) -> BookmarkAsset:
    asset = BookmarkAsset(
        bookmark=bookmark,
        asset_type=BookmarkAsset.TYPE_UPLOAD,
        content_type=upload_file.content_type,
        display_name=upload_file.name,
        status=BookmarkAsset.STATUS_PENDING,
        gzip=False,
    )
    asset.save()

    try:
        filename = _generate_upload_asset_filename(asset, upload_file.name)
        filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
        with open(filepath, "wb") as f:
            for chunk in upload_file.chunks():
                f.write(chunk)
        asset.status = BookmarkAsset.STATUS_COMPLETE
        asset.file = filename
        asset.file_size = upload_file.size
        logger.info(
            f"Successfully uploaded asset file. bookmark={bookmark} file={upload_file.name}"
        )
    except Exception as e:
        logger.error(
            f"Failed to upload asset file. bookmark={bookmark} file={upload_file.name}",
            exc_info=e,
        )
        asset.status = BookmarkAsset.STATUS_FAILURE

    asset.save()

    return asset


def _merge_bookmark_data(from_bookmark: Bookmark, to_bookmark: Bookmark):
    to_bookmark.title = from_bookmark.title
    to_bookmark.description = from_bookmark.description
    to_bookmark.notes = from_bookmark.notes
    to_bookmark.unread = from_bookmark.unread
    to_bookmark.shared = from_bookmark.shared


def _update_bookmark_tags(bookmark: Bookmark, tag_string: str, user: User):
    tag_names = parse_tag_string(tag_string)

    if user.profile.auto_tagging_rules:
        try:
            auto_tag_names = auto_tagging.get_tags(
                user.profile.auto_tagging_rules, bookmark.url
            )
            for auto_tag_name in auto_tag_names:
                if auto_tag_name not in tag_names:
                    tag_names.append(auto_tag_name)
        except Exception as e:
            logger.error(
                f"Failed to auto-tag bookmark. url={bookmark.url}",
                exc_info=e,
            )

    tags = get_or_create_tags(tag_names, user)
    bookmark.tags.set(tags)


def _sanitize_id_list(bookmark_ids: [Union[int, str]]) -> [int]:
    # Convert string ids to int if necessary
    return [int(bm_id) if isinstance(bm_id, str) else bm_id for bm_id in bookmark_ids]
