import logging
import os.path
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings

max_file_age = 60 * 60 * 24  # 1 day

logger = logging.getLogger(__name__)


def _ensure_favicon_folder():
    Path(settings.LD_FAVICON_FOLDER).mkdir(parents=True, exist_ok=True)


def _url_to_filename(url: str) -> str:
    name = re.sub(r'\W+', '_', url)
    return f'{name}.png'


def _get_url_parameters(url: str) -> dict:
    parsed_uri = urlparse(url)
    return {
        # https://example.com/foo?bar -> https://example.com
        'url': f'{parsed_uri.scheme}://{parsed_uri.hostname}',
        # https://example.com/foo?bar -> example.com
        'domain': parsed_uri.hostname,
    }


def _get_favicon_path(favicon_file: str) -> Path:
    return Path(os.path.join(settings.LD_FAVICON_FOLDER, favicon_file))


def _is_stale(path: Path) -> bool:
    stat = path.stat()
    file_age = time.time() - stat.st_mtime
    return file_age >= max_file_age


def load_favicon(url: str) -> str:
    url_parameters = _get_url_parameters(url)

    # Use scheme+hostname as favicon filename to reuse icon for all pages on the same domain
    favicon_name = _url_to_filename(url_parameters['url'])
    favicon_path = _get_favicon_path(favicon_name)

    # Load icon if it doesn't exist yet or has become stale
    if not favicon_path.exists() or _is_stale(favicon_path):
        # Create favicon folder if not exists
        _ensure_favicon_folder()
        # Load favicon from provider, save to file
        favicon_url = settings.LD_FAVICON_PROVIDER.format(**url_parameters)
        logger.debug(f'Loading favicon from: {favicon_url}')
        with requests.get(favicon_url, stream=True) as response:
            with open(favicon_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        logger.debug(f'Saved favicon as: {favicon_path}')

    return favicon_name
