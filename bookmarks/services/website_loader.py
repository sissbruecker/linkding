import logging
from dataclasses import dataclass
from functools import lru_cache

import requests
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class WebsiteMetadata:
    url: str
    title: str
    description: str

    def to_dict(self):
        return {
            'url': self.url,
            'title': self.title,
            'description': self.description,
        }


# Caching metadata avoids scraping again when saving bookmarks, in case the
# metadata was already scraped to show preview values in the bookmark form
@lru_cache(maxsize=10)
def load_website_metadata(url: str):
    title = None
    description = None
    try:
        start = timezone.now()
        page_text = load_page(url)
        end = timezone.now()
        logger.debug(f'Load duration: {end - start}')

        start = timezone.now()
        soup = BeautifulSoup(page_text, 'html.parser')

        title = soup.title.string.strip() if soup.title is not None else None
        description_tag = soup.find('meta', attrs={'name': 'description'})
        description = description = description_tag['content'].strip() if description_tag and description_tag[
            'content'] else None
        end = timezone.now()
        logger.debug(f'Parsing duration: {end - start}')
    finally:
        return WebsiteMetadata(url=url, title=title, description=description)


CHUNK_SIZE = 50 * 1024
MAX_CONTENT_LIMIT = 5000 * 1024


def load_page(url: str):
    headers = fake_request_headers()
    size = 0
    content = None
    iteration = 0
    # Use with to ensure request gets closed even if it's only read partially
    with requests.get(url, timeout=10, headers=headers, stream=True) as r:
        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            size += len(chunk)
            iteration = iteration + 1
            if content is None:
                content = chunk
            else:
                content = content + chunk

            logger.debug(f'Loaded chunk (iteration={iteration}, total={size / 1024})')

            # Stop reading if we have parsed end of head tag
            if '</head>'.encode('utf-8') in content:
                logger.debug(f'Found closing head tag after {size} bytes')
                break
            # Stop reading if we exceed limit
            if size > MAX_CONTENT_LIMIT:
                logger.debug(f'Cancel reading document after {size} bytes')
                break
        if hasattr(r, '_content_consumed'):
            logger.debug(f'Request consumed: {r._content_consumed}')

    # Use charset_normalizer to determine encoding that best matches the response content
    # Several sites seem to specify the response encoding incorrectly, so we ignore it and use custom logic instead
    # This is different from Response.text which does respect the encoding specified in the response first,
    # before trying to determine one
    results = from_bytes(content or '')
    return str(results.best())


DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36'


def fake_request_headers():
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Encoding": "gzip, deflate",
        "Dnt": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": DEFAULT_USER_AGENT,
    }
