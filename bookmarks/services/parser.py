from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, List

from bookmarks.models import parse_tag_string


@dataclass
class NetscapeBookmark:
    href: str
    title: str
    description: str
    notes: str
    date_added: str
    date_modified: str
    tag_names: List[str]
    to_read: bool
    private: bool
    archived: bool


class BookmarkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.bookmarks = []

        self.current_tag = None
        self.bookmark = None
        self.href = ""
        self.add_date = ""
        self.last_modified = ""
        self.tags = ""
        self.title = ""
        self.description = ""
        self.notes = ""
        self.toread = ""
        self.private = ""

    def handle_starttag(self, tag: str, attrs: list):
        name = "handle_start_" + tag.lower()
        if name in dir(self):
            getattr(self, name)({k.lower(): v for k, v in attrs})
        self.current_tag = tag

    def handle_endtag(self, tag: str):
        name = "handle_end_" + tag.lower()
        if name in dir(self):
            getattr(self, name)()
        self.current_tag = None

    def handle_data(self, data):
        name = f"handle_{self.current_tag}_data"
        if name in dir(self):
            getattr(self, name)(data)

    def handle_end_dl(self):
        self.add_bookmark()

    def handle_start_dt(self, attrs: Dict[str, str]):
        self.add_bookmark()

    def handle_start_a(self, attrs: Dict[str, str]):
        vars(self).update(attrs)
        tag_names = parse_tag_string(self.tags)
        archived = "linkding:archived" in self.tags
        try:
            tag_names.remove("linkding:archived")
        except ValueError:
            pass

        self.bookmark = NetscapeBookmark(
            href=self.href,
            title="",
            description="",
            notes="",
            date_added=self.add_date,
            date_modified=self.last_modified,
            tag_names=tag_names,
            to_read=self.toread == "1",
            # Mark as private by default, also when attribute is not specified
            private=self.private != "0",
            archived=archived,
        )

    def handle_a_data(self, data):
        self.title = data.strip()

    def handle_dd_data(self, data):
        desc = data.strip()
        if "[linkding-notes]" in desc:
            self.notes = desc.split("[linkding-notes]")[1].split("[/linkding-notes]")[0]
        self.description = desc.split("[linkding-notes]")[0]

    def add_bookmark(self):
        if self.bookmark:
            self.bookmark.title = self.title
            self.bookmark.description = self.description
            self.bookmark.notes = self.notes
            self.bookmarks.append(self.bookmark)
        self.bookmark = None
        self.href = ""
        self.add_date = ""
        self.last_modified = ""
        self.tags = ""
        self.title = ""
        self.description = ""
        self.notes = ""
        self.toread = ""
        self.private = ""


def parse(html: str) -> List[NetscapeBookmark]:
    parser = BookmarkParser()
    parser.feed(html)
    return parser.bookmarks
