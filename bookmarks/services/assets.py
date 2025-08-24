import gzip
import logging
import os
import shutil

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone, formats

from bookmarks.models import Bookmark, BookmarkAsset
from bookmarks.services import singlefile

MAX_ASSET_FILENAME_LENGTH = 192

logger = logging.getLogger(__name__)


def create_snapshot_asset(bookmark: Bookmark) -> BookmarkAsset:
    date_created = timezone.now()
    timestamp = formats.date_format(date_created, "SHORT_DATE_FORMAT")
    asset = BookmarkAsset(
        bookmark=bookmark,
        asset_type=BookmarkAsset.TYPE_SNAPSHOT,
        date_created=date_created,
        content_type=BookmarkAsset.CONTENT_TYPE_HTML,
        display_name=f"HTML snapshot from {timestamp}",
        status=BookmarkAsset.STATUS_PENDING,
    )
    return asset


def create_snapshot(asset: BookmarkAsset):
    try:
        # Create snapshot into temporary file
        temp_filename = _generate_asset_filename(asset, asset.bookmark.url, "tmp")
        temp_filepath = os.path.join(settings.LD_ASSET_FOLDER, temp_filename)
        singlefile.create_snapshot(asset.bookmark.url, temp_filepath)

        # Store as gzip in asset folder
        filename = _generate_asset_filename(asset, asset.bookmark.url, "html.gz")
        filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
        with (
            open(temp_filepath, "rb") as temp_file,
            gzip.open(filepath, "wb") as gz_file,
        ):
            shutil.copyfileobj(temp_file, gz_file)

        # Remove temporary file
        os.remove(temp_filepath)

        asset.status = BookmarkAsset.STATUS_COMPLETE
        asset.file = filename
        asset.gzip = True
        asset.save()

        asset.bookmark.latest_snapshot = asset
        asset.bookmark.date_modified = timezone.now()
        asset.bookmark.save()
    except Exception as error:
        asset.status = BookmarkAsset.STATUS_FAILURE
        asset.save()
        raise error


def upload_snapshot(bookmark: Bookmark, html: bytes):
    asset = create_snapshot_asset(bookmark)
    filename = _generate_asset_filename(asset, asset.bookmark.url, "html.gz")
    filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)

    with gzip.open(filepath, "wb") as gz_file:
        gz_file.write(html)

    # Only save the asset if the file was written successfully
    asset.status = BookmarkAsset.STATUS_COMPLETE
    asset.file = filename
    asset.gzip = True
    asset.save()

    asset.bookmark.latest_snapshot = asset
    asset.bookmark.date_modified = timezone.now()
    asset.bookmark.save()

    return asset


def upload_asset(bookmark: Bookmark, upload_file: UploadedFile):
    try:
        asset = BookmarkAsset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_UPLOAD,
            date_created=timezone.now(),
            content_type=upload_file.content_type,
            display_name=upload_file.name,
            status=BookmarkAsset.STATUS_COMPLETE,
            gzip=False,
        )
        name, extension = os.path.splitext(upload_file.name)

        # automatically gzip the file if it is not already gzipped
        if upload_file.content_type != "application/gzip":
            filename = _generate_asset_filename(
                asset, name, extension.lstrip(".") + ".gz"
            )
            filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
            with gzip.open(filepath, "wb", compresslevel=9) as f:
                for chunk in upload_file.chunks():
                    f.write(chunk)
            asset.gzip = True
            asset.file = filename
            asset.file_size = os.path.getsize(filepath)
        else:
            filename = _generate_asset_filename(asset, name, extension.lstrip("."))
            filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
            with open(filepath, "wb") as f:
                for chunk in upload_file.chunks():
                    f.write(chunk)
            asset.file = filename
            asset.file_size = upload_file.size

        asset.save()

        asset.bookmark.date_modified = timezone.now()
        asset.bookmark.save()

        logger.info(
            f"Successfully uploaded asset file. bookmark={bookmark} file={upload_file.name}"
        )
        return asset
    except Exception as e:
        logger.error(
            f"Failed to upload asset file. bookmark={bookmark} file={upload_file.name}",
            exc_info=e,
        )
        raise e


def remove_asset(asset: BookmarkAsset):
    # If this asset is the latest_snapshot for a bookmark, try to find the next most recent snapshot
    bookmark = asset.bookmark
    if bookmark and bookmark.latest_snapshot == asset:
        latest = (
            BookmarkAsset.objects.filter(
                bookmark=bookmark,
                asset_type=BookmarkAsset.TYPE_SNAPSHOT,
                status=BookmarkAsset.STATUS_COMPLETE,
            )
            .exclude(pk=asset.pk)
            .order_by("-date_created")
            .first()
        )

        bookmark.latest_snapshot = latest

    asset.delete()
    bookmark.date_modified = timezone.now()
    bookmark.save()


def _generate_asset_filename(
    asset: BookmarkAsset, filename: str, extension: str
) -> str:
    def sanitize_char(char):
        if char.isalnum() or char in ("-", "_", "."):
            return char
        else:
            return "_"

    formatted_datetime = asset.date_created.strftime("%Y-%m-%d_%H%M%S")
    sanitized_filename = "".join(sanitize_char(char) for char in filename)

    # Calculate the length of fixed parts of the final filename
    non_filename_length = len(f"{asset.asset_type}_{formatted_datetime}_.{extension}")
    # Calculate the maximum length for the dynamic part of the filename
    max_filename_length = MAX_ASSET_FILENAME_LENGTH - non_filename_length
    # Truncate the filename if necessary
    sanitized_filename = sanitized_filename[:max_filename_length]

    return f"{asset.asset_type}_{formatted_datetime}_{sanitized_filename}.{extension}"
