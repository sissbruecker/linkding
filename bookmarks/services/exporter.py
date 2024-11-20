import html
import itertools
from typing import Iterable

from bookmarks.models import Bookmark


def export_netscape_html(bookmarks: Iterable[Bookmark]):
    def _append_bookmarks():
        for bookmark in bookmarks:
            yield from append_bookmark(bookmark)

    return itertools.chain(append_header(), append_list_start(), _append_bookmarks(), append_list_end())


def append_header():
    yield "<!DOCTYPE NETSCAPE-Bookmark-file-1>"
    yield '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">'
    yield "<TITLE>Bookmarks</TITLE>"
    yield "<H1>Bookmarks</H1>"


def append_list_start():
    yield "<DL><p>"


def append_bookmark(bookmark: Bookmark):
    url = bookmark.url
    title = html.escape(bookmark.resolved_title or "")
    desc = html.escape(bookmark.resolved_description or "")
    if bookmark.notes:
        desc += f"[linkding-notes]{html.escape(bookmark.notes)}[/linkding-notes]"
    tag_names = bookmark.tag_names
    if bookmark.is_archived:
        tag_names.append("linkding:archived")
    tags = ",".join(tag_names)
    toread = "1" if bookmark.unread else "0"
    private = "0" if bookmark.shared else "1"
    added = int(bookmark.date_added.timestamp())
    modified = int(bookmark.date_modified.timestamp())

    yield  f'<DT><A HREF="{url}" ADD_DATE="{added}" LAST_MODIFIED="{modified}" PRIVATE="{private}" TOREAD="{toread}" TAGS="{tags}">{title}</A>'
    

    if desc:
        yield f"<DD>{desc}"


def append_list_end():
    yield "</DL><p>"
