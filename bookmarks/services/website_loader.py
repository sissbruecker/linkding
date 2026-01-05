import logging
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class WebsiteMetadata:
    url: str
    title: str | None
    description: str | None
    preview_image: str | None

    def to_dict(self):
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "preview_image": self.preview_image,
        }


def load_website_metadata(url: str, ignore_cache: bool = False):
    if ignore_cache:
        return _load_website_metadata(url)
    return _load_website_metadata_cached(url)


# Caching metadata avoids scraping again when saving bookmarks, in case the
# metadata was already scraped to show preview values in the bookmark form
@lru_cache(maxsize=10)
def _load_website_metadata_cached(url: str):
    return _load_website_metadata(url)


def _load_website_metadata(url: str):
    title = None
    description = None
    preview_image = None
    try:
        start = timezone.now()
        page_text = load_page(url)
        end = timezone.now()
        logger.debug(f"Load duration: {end - start}")

        start = timezone.now()
        soup = BeautifulSoup(page_text, "html.parser")

        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = (
            description_tag["content"].strip()
            if description_tag and description_tag["content"]
            else None
        )

        if not description:
            description_tag = soup.find("meta", attrs={"property": "og:description"})
            description = (
                description_tag["content"].strip()
                if description_tag and description_tag["content"]
                else None
            )

        image_tag = soup.find("meta", attrs={"property": "og:image"})
        preview_image = image_tag["content"].strip() if image_tag else None
        if (
            preview_image
            and not preview_image.startswith("http://")
            and not preview_image.startswith("https://")
        ):
            preview_image = urljoin(url, preview_image)

        end = timezone.now()
        logger.debug(f"Parsing duration: {end - start}")
    except Exception:
        pass

    return WebsiteMetadata(
        url=url, title=title, description=description, preview_image=preview_image
    )


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
            content = chunk if content is None else content + chunk

            logger.debug(f"Loaded chunk (iteration={iteration}, total={size / 1024})")

            # Stop reading if we have parsed end of head tag
            end_of_head = b"</head>"
            if end_of_head in content:
                logger.debug(f"Found closing head tag after {size} bytes")
                content = content.split(end_of_head)[0] + end_of_head
                break
            # Stop reading if we exceed limit
            if size > MAX_CONTENT_LIMIT:
                logger.debug(f"Cancel reading document after {size} bytes")
                break
        if hasattr(r, "_content_consumed"):
            logger.debug(f"Request consumed: {r._content_consumed}")

    # Use charset_normalizer to determine encoding that best matches the response content
    # Several sites seem to specify the response encoding incorrectly, so we ignore it and use custom logic instead
    # This is different from Response.text which does respect the encoding specified in the response first,
    # before trying to determine one
    results = from_bytes(content or "")
    return str(results.best())


DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36"


def fake_request_headers():
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Encoding": "gzip, deflate",
        "Dnt": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": DEFAULT_USER_AGENT,
    }


def detect_content_type(url: str, timeout: int = 10) -> str | None:
    """Make HEAD request to detect content type of URL. Returns None on failure."""
    headers = fake_request_headers()

    try:
        response = requests.head(
            url, headers=headers, timeout=timeout, allow_redirects=True
        )
        if response.status_code == 200:
            return (
                response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            )
    except requests.RequestException:
        pass

    try:
        with requests.get(
            url, headers=headers, timeout=timeout, stream=True, allow_redirects=True
        ) as response:
            if response.status_code == 200:
                return (
                    response.headers.get("Content-Type", "")
                    .split(";")[0]
                    .strip()
                    .lower()
                )
    except requests.RequestException:
        pass

    return None


def is_pdf_content_type(content_type: str | None) -> bool:
    """Check if the content type indicates a PDF."""
    if not content_type:
        return False
    return content_type in ("application/pdf", "application/x-pdf")
