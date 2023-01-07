import os.path
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings


def _url_to_filename(url: str) -> str:
    name = re.sub(r'\W+', '_', url)
    return f'{name}.png'


def _ensure_favicon_folder():
    Path(settings.LD_FAVICON_FOLDER).mkdir(parents=True, exist_ok=True)


def _get_base_url(url: str) -> str:
    parsed_uri = urlparse(url)
    return f'{parsed_uri.scheme}://{parsed_uri.hostname}'


def _get_favicon_path(base_url: str) -> str:
    favicon_name = _url_to_filename(base_url)
    return os.path.join(settings.LD_FAVICON_FOLDER, favicon_name)


def check_favicon(url: str) -> bool:
    base_url = _get_base_url(url)
    favicon_path = _get_favicon_path(base_url)
    return Path(favicon_path).exists()


def load_favicon(url: str):
    # Create favicon folder if not exists
    _ensure_favicon_folder()
    # Get base URL so that we can reuse favicons for multiple bookmarks with the same host
    base_url = _get_base_url(url)
    # Load favicon from provider, save to file
    favicon_url = settings.LD_FAVICON_PROVIDER.format(url=base_url)
    favicon_path = _get_favicon_path(base_url)
    response = requests.get(favicon_url, stream=True)

    with open(favicon_path, 'wb') as file:
        shutil.copyfileobj(response.raw, file)

    del response
