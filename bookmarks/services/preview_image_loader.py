import logging
import mimetypes
import os.path
import hashlib
from pathlib import Path

import requests
from django.conf import settings
from bookmarks.services import website_loader

logger = logging.getLogger(__name__)


def _ensure_preview_folder():
    Path(settings.LD_PREVIEW_FOLDER).mkdir(parents=True, exist_ok=True)


def _url_to_filename(preview_image: str) -> str:
    return hashlib.md5(preview_image.encode()).hexdigest()


def _get_image_path(preview_image_file: str) -> Path:
    return Path(os.path.join(settings.LD_PREVIEW_FOLDER, preview_image_file))


def load_preview_image(url: str) -> str | None:
    _ensure_preview_folder()

    metadata = website_loader.load_website_metadata(url)
    if not metadata.preview_image:
        logger.debug(f"Could not find preview image in metadata: {url}")
        return None

    logger.debug(f"Loading preview image: {metadata.preview_image}")
    with requests.get(metadata.preview_image, stream=True) as response:
        content_type = response.headers["Content-Type"]
        preview_image_hash = _url_to_filename(url)
        file_extension = mimetypes.guess_extension(content_type)
        preview_image_file = f"{preview_image_hash}{file_extension}"
        preview_image_path = _get_image_path(preview_image_file)
        with open(preview_image_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    logger.debug(f"Saved preview image as: {preview_image_path}")

    return preview_image_file
