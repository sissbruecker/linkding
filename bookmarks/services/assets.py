import gzip
import logging
import os
import shutil

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone, formats

from bookmarks.models import Bookmark, BookmarkAsset
from bookmarks.services import singlefile
from bookmarks.services import trafilatura_extractor

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


def _try_trafilatura_snapshot(url: str, filepath: str) -> bool:
    """Try to create snapshot using Trafilatura. Returns True on success."""
    try:
        import trafilatura
        logger.info(f"Creating snapshot with Trafilatura for {url}")
        trafilatura_extractor.create_snapshot(url, filepath)
        return True
    except ImportError:
        logger.warning("Trafilatura not available")
        return False
    except Exception as e:
        logger.warning(f"Trafilatura failed for {url}: {e}")
        return False


def _try_singlefile_snapshot(url: str, filepath: str) -> bool:
    """Try to create snapshot using SingleFile. Returns True on success."""
    try:
        logger.info(f"Creating snapshot with SingleFile for {url}")
        singlefile.create_snapshot(url, filepath)
        return True
    except FileNotFoundError:
        logger.warning("SingleFile CLI not available")
        return False
    except Exception as e:
        logger.warning(f"SingleFile failed for {url}: {e}")
        return False


def create_snapshot(asset: BookmarkAsset):
    try:
        # Create snapshot into temporary file
        temp_filename = _generate_asset_filename(asset, asset.bookmark.url, "tmp")
        temp_filepath = os.path.join(settings.LD_ASSET_FOLDER, temp_filename)
        
        # Choose archiver based on configuration with fallback logic
        archiver_type = getattr(settings, 'LD_ARCHIVER_TYPE', 'singlefile').lower()
        
        # Try preferred archiver first, then fallback
        success = False
        
        if archiver_type == 'trafilatura':
            success = _try_trafilatura_snapshot(asset.bookmark.url, temp_filepath)
            if not success:
                logger.warning(f"Trafilatura failed for {asset.bookmark.url}")
        else:
            # Default to SingleFile (backward compatibility)
            success = _try_singlefile_snapshot(asset.bookmark.url, temp_filepath)
            if not success and archiver_type != 'singlefile':
                # If explicitly configured SingleFile fails, try Trafilatura
                logger.warning(f"SingleFile failed for {asset.bookmark.url}, trying Trafilatura fallback")
                success = _try_trafilatura_snapshot(asset.bookmark.url, temp_filepath)
        
            if not success:
                raise Exception("Both Trafilatura and SingleFile failed to create snapshot")

        # Store as gzip in asset folder
        filename = _generate_asset_filename(asset, asset.bookmark.url, "html.gz")
        filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
        with open(temp_filepath, "rb") as temp_file, gzip.open(
            filepath, "wb"
        ) as gz_file:
            shutil.copyfileobj(temp_file, gz_file)

        # Remove temporary file
        os.remove(temp_filepath)

        asset.status = BookmarkAsset.STATUS_COMPLETE
        asset.file = filename
        asset.gzip = True
        asset.save()

        asset.bookmark.latest_snapshot = asset
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
        filename = _generate_asset_filename(asset, name, extension.lstrip("."))
        filepath = os.path.join(settings.LD_ASSET_FOLDER, filename)
        with open(filepath, "wb") as f:
            for chunk in upload_file.chunks():
                f.write(chunk)
        asset.file = filename
        asset.file_size = upload_file.size
        asset.save()
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
        bookmark.save()

    asset.delete()


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
