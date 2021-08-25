from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes


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


def load_website_metadata(url: str):
    title = None
    description = None
    try:
        page_text = load_page(url)
        soup = BeautifulSoup(page_text, 'html.parser')

        title = soup.title.string if soup.title is not None else None
        description_tag = soup.find('meta', attrs={'name': 'description'})
        description = description_tag['content'] if description_tag is not None else None
    finally:
        return WebsiteMetadata(url=url, title=title, description=description)


def load_page(url: str):
    r = requests.get(url, timeout=10)

    # Use charset_normalizer to determine encoding that best matches the response content
    # Several sites seem to specify the response encoding incorrectly, so we ignore it and use custom logic instead
    # This is different from Response.text which does respect the encoding specified in the response first,
    # before trying to determine one
    results = from_bytes(r.content)
    return str(results.best())
