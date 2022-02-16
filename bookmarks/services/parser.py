from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, List, Optional

import pyparsing as pp


@dataclass
class NetscapeBookmark:
    href: str
    title: str
    description: str
    date_added: str
    tag_string: str


class BookmarkParser(HTMLParser):

    tag_stack: List[Optional[str]] = []
    tag: Optional[str] = None
    bookmarks: List[NetscapeBookmark] = []
    bookmark: Optional[NetscapeBookmark] = None
    folder: Optional[str] = ''
    description: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list):
        name = 'handle_start_' + tag.lower()
        if name in dir(self):
            getattr(self, name)({k.lower(): v for k, v in attrs})
        self.tag = tag

    def handle_endtag(self, tag: str):
        name = 'handle_end_' + tag.lower()
        if name in dir(self):
            getattr(self, name)()
        self.tag = None

    def handle_data(self, data):
        name = f'handle_{self.tag}_data'
        if name in dir(self):
            getattr(self, name)(data)

    def handle_start_dl(self, attrs: Dict[str, str]):
        print('<DL>')
        self.tag_stack.append(None)
        self.description = None

    def handle_end_dl(self):
        print('</DL>')
        self.add_bookmark()
        self.tag_stack.pop()

    def handle_start_dt(self, attrs: Dict[str, str]):
        self.add_bookmark()

    def handle_start_a(self, attrs: Dict[str, str]):
        print(f'<A {attrs}>')
        vars(self).update(attrs)

    def handle_a_data(self, data):
        print('<A>data:', data)
        print(' self:', self.href, self.add_date)
        print(' stack:', self.tag_stack)
        self.bookmark = NetscapeBookmark(
            href=self.href,
            title=data,
            description=self.description,
            date_added=self.add_date,
            tag_string=','.join(self.tag_stack[:-1]),
        )

    def handle_h3_data(self, data):
        print('<H3>data:', data)
        self.tag_stack[-1] = data.strip()

    def handle_dd_data(self, data):
        self.description = data.strip()

    def add_bookmark(self):
        if self.bookmark:
            self.bookmarks.append(self.bookmark)
        self.bookmark = None


def extract_bookmark_link(tag):
    href = tag[0].href
    title = tag[0].text
    tag_string = tag[0].tags
    date_added = tag[0].add_date

    return {'href': href, 'title': title, 'tag_string': tag_string, 'date_added': date_added}


def extract_bookmark(tag):
    link = tag[0].link
    description = tag[0].description
    description = description[0] if description else ''

    return {
        'link': link,
        'description': description,
    }


def extract_description(tag):
    return tag[0].strip()


# define grammar
dt_start, _ = pp.makeHTMLTags("DT")
dd_start, _ = pp.makeHTMLTags("DD")
a_start, a_end = pp.makeHTMLTags("A")
bookmark_link_tag = pp.Group(a_start + a_start.tag_body("text") + a_end.suppress())
bookmark_link_tag.addParseAction(extract_bookmark_link)
bookmark_description_tag = dd_start.suppress() + pp.SkipTo(pp.anyOpenTag | pp.anyCloseTag)("description")
bookmark_description_tag.addParseAction(extract_description)
bookmark_tag = pp.Group(dt_start + bookmark_link_tag("link") + pp.ZeroOrMore(bookmark_description_tag)("description"))
bookmark_tag.addParseAction(extract_bookmark)


def parse(html: str) -> List[NetscapeBookmark]:
    matches = bookmark_tag.searchString(html)
    bookmarks = []

    for match in matches:
        bookmark_match = match[0]
        bookmark = NetscapeBookmark(
            href=bookmark_match['link']['href'],
            title=bookmark_match['link']['title'],
            description=bookmark_match['description'],
            tag_string=bookmark_match['link']['tag_string'],
            date_added=bookmark_match['link']['date_added'],
        )
        bookmarks.append(bookmark)

    return bookmarks


def parse_with_folders(html: str) -> List[NetscapeBookmark]:
    parser = BookmarkParser()
    parser.feed(html)
    return parser.bookmarks
