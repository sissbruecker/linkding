import os.path
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings

max_file_age = 60 * 60 * 24  # 1 day


def _ensure_favicon_folder():
    Path(settings.LD_FAVICON_FOLDER).mkdir(parents=True, exist_ok=True)


def _url_to_filename(url: str) -> str:
    name = re.sub(r'\W+', '_', url)
    return f'{name}.png'


def _get_base_url(url: str) -> str:
    parsed_uri = urlparse(url)
    return f'{parsed_uri.scheme}://{parsed_uri.hostname}'


def _get_favicon_path(favicon_file: str) -> Path:
    return Path(os.path.join(settings.LD_FAVICON_FOLDER, favicon_file))


def _is_stale(path: Path) -> bool:
    stat = path.stat()
    file_age = time.time() - stat.st_mtime
    return file_age >= max_file_age


def load_favicon(url: str) -> str:
    # Get base URL so that we can reuse favicons for multiple bookmarks with the same host
    base_url = _get_base_url(url)
    favicon_name = _url_to_filename(base_url)
    favicon_path = _get_favicon_path(favicon_name)

    # Load icon if it doesn't exist yet or has become stale
    if not favicon_path.exists() or _is_stale(favicon_path):
        # Create favicon folder if not exists
        _ensure_favicon_folder()
        # Load favicon from provider, save to file
        favicon_url = settings.LD_FAVICON_PROVIDER.format(url=base_url)
        response = requests.get(favicon_url, stream=True)

        with open(favicon_path, 'wb') as file:
            shutil.copyfileobj(response.raw, file)

        del response

    return favicon_name
