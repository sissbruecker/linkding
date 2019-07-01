from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


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
    r = requests.get(url)
    return r.text
