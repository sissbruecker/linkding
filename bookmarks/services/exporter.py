import html
from typing import List

from bookmarks.models import Bookmark

BookmarkDocument = List[str]


def export_netscape_html(bookmarks: List[Bookmark]):
    doc = []
    append_header(doc)
    append_list_start(doc)
    [append_bookmark(doc, bookmark) for bookmark in bookmarks]
    append_list_end(doc)

    return "\n\r".join(doc)


def append_header(doc: BookmarkDocument):
    doc.append("<!DOCTYPE NETSCAPE-Bookmark-file-1>")
    doc.append('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">')
    doc.append("<TITLE>Bookmarks</TITLE>")
    doc.append("<H1>Bookmarks</H1>")


def append_list_start(doc: BookmarkDocument):
    doc.append("<DL><p>")


def append_bookmark(doc: BookmarkDocument, bookmark: Bookmark):
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

    doc.append(
        f'<DT><A HREF="{url}" ADD_DATE="{added}" LAST_MODIFIED="{modified}" PRIVATE="{private}" TOREAD="{toread}" TAGS="{tags}">{title}</A>'
    )

    if desc:
        doc.append(f"<DD>{desc}")


def append_list_end(doc: BookmarkDocument):
    doc.append("</DL><p>")
