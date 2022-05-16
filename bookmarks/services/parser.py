from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, List


@dataclass
class NetscapeBookmark:
    href: str
    title: str
    description: str
    date_added: str
    tag_string: str


class BookmarkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.add_date = None
        self.tags = None
        self.description = None

        self.current_tag = None
        self.bookmarks = []
        self.bookmark = None

    def handle_starttag(self, tag: str, attrs: list):
        name = 'handle_start_' + tag.lower()
        if name in dir(self):
            getattr(self, name)({k.lower(): v for k, v in attrs})
        self.current_tag = tag

    def handle_endtag(self, tag: str):
        name = 'handle_end_' + tag.lower()
        if name in dir(self):
            getattr(self, name)()
        self.current_tag = None

    def handle_data(self, data):
        name = f'handle_{self.current_tag}_data'
        if name in dir(self):
            getattr(self, name)(data)

    def handle_start_dl(self, attrs: Dict[str, str]):
        self.description = None

    def handle_end_dl(self):
        self.add_bookmark()

    def handle_start_dt(self, attrs: Dict[str, str]):
        self.add_bookmark()

    def handle_start_a(self, attrs: Dict[str, str]):
        vars(self).update(attrs)

    def handle_a_data(self, data):
        self.bookmark = NetscapeBookmark(
            href=self.href,
            title=data,
            description='',
            date_added=self.add_date,
            tag_string=self.tags,
        )

    def handle_dd_data(self, data):
        if self.bookmark:
            self.bookmark.description = data.strip()

    def add_bookmark(self):
        if self.bookmark:
            self.bookmarks.append(self.bookmark)
        self.bookmark = None
        self.href = None
        self.description = None
        self.add_date = None
        self.tags = None


def parse(html: str) -> List[NetscapeBookmark]:
    parser = BookmarkParser()
    parser.feed(html)
    return parser.bookmarks
