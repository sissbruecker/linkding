from dataclasses import dataclass
from datetime import datetime

import pyparsing as pp


@dataclass
class NetscapeBookmark:
    href: str
    title: str
    description: str
    date_added: int
    tag_string: str


def extract_bookmark_link(tag):
    href = tag[0].href
    title = tag[0].text
    tag_string = tag[0].tags
    date_added_string = tag[0].add_date if tag[0].add_date else datetime.now().timestamp()
    date_added = int(date_added_string)

    return {
        'href': href,
        'title': title,
        'tag_string': tag_string,
        'date_added': date_added
    }


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


def parse(html: str) -> [NetscapeBookmark]:
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
