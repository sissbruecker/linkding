import logging
import mimetypes
import os.path
import hashlib
from pathlib import Path

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _ensure_preview_folder():
    Path(settings.LD_PREVIEW_FOLDER).mkdir(parents=True, exist_ok=True)


def _url_to_filename(preview_image: str) -> str:
    return hashlib.md5(preview_image.encode()).hexdigest()


def _get_image_path(preview_image_file: str) -> Path:
    return Path(os.path.join(settings.LD_PREVIEW_FOLDER, preview_image_file))


def _check_existing_preview_image(preview_image_hash: str):
    # return existing file if a file with the same name, ignoring extension
    for filename in os.listdir(settings.LD_PREVIEW_FOLDER):
        file_base_name, _ = os.path.splitext(filename)
        if file_base_name == preview_image_hash:
            return filename
    return None


def load_preview_image(preview_image: str) -> str:
    _ensure_preview_folder()

    preview_image_hash = _url_to_filename(preview_image)
    preview_image_file = _check_existing_preview_image(preview_image_hash)

    if not preview_image_file:
        logger.debug(f"Loading preview image: {preview_image}")
        with requests.get(preview_image, stream=True) as response:
            content_type = response.headers["Content-Type"]
            file_extension = mimetypes.guess_extension(content_type)
            preview_image_file = f"{preview_image_hash}{file_extension}"
            preview_image_path = _get_image_path(preview_image_file)
            with open(preview_image_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        logger.debug(f"Saved preview image as: {preview_image_path}")

    return preview_image_file
