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

    image_url = metadata.preview_image

    logger.debug(f"Loading preview image: {image_url}")
    with requests.get(image_url, stream=True) as response:
        if response.status_code < 200 or response.status_code >= 300:
            logger.debug(
                f"Bad response status code for preview image: {image_url} status_code={response.status_code}"
            )
            return None

        if "Content-Length" not in response.headers:
            logger.debug(f"Empty Content-Length for preview image: {image_url}")
            return None

        content_length = int(response.headers["Content-Length"])
        if content_length > settings.LD_PREVIEW_MAX_SIZE:
            logger.debug(
                f"Content-Length exceeds LD_PREVIEW_MAX_SIZE: {image_url} length={content_length}"
            )
            return None

        if "Content-Type" not in response.headers:
            logger.debug(f"Empty Content-Type for preview image: {image_url}")
            return None

        content_type = response.headers["Content-Type"].split(";", 1)[0]
        file_extension = mimetypes.guess_extension(content_type)

        if file_extension not in settings.LD_PREVIEW_ALLOWED_EXTENSIONS:
            logger.debug(
                f"Unsupported Content-Type for preview image: {image_url} content_type={content_type}"
            )
            return None

        preview_image_hash = _url_to_filename(url)
        preview_image_file = f"{preview_image_hash}{file_extension}"
        preview_image_path = _get_image_path(preview_image_file)

        with open(preview_image_path, "wb") as file:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded > content_length:
                    logger.debug(
                        f"Content-Length mismatch for preview image: {image_url} length={content_length} downloaded={downloaded}"
                    )
                    file.close()
                    preview_image_path.unlink()
                    return None

                file.write(chunk)

    logger.debug(f"Saved preview image as: {preview_image_path}")

    return preview_image_file
