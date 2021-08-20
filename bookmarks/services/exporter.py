from typing import List
from datetime import datetime

from django.utils import timezone

from bookmarks.models import Bookmark
from bookmarks.services.parser import NetscapeBookmarkFileData

BookmarkDocument = List[str]


def export_netscape_html(netscape_data: NetscapeBookmarkFileData):
    doc = []
    append_header(doc)
    doc.append('')
    export_netscape_data(doc, netscape_data)

    return '\n'.join(doc)

def export_netscape_data(doc: BookmarkDocument, netscape_data: NetscapeBookmarkFileData, indent: str = ''):
    if netscape_data.folder != '':
        now = int(timezone.now().timestamp())
        doc.append(f'{indent}<DT><H3 ADD_DATE="{now}">{netscape_data.folder}</H3>')
    doc.append(f'{indent}<DL><p>')
    [append_bookmark(doc, bookmark, indent+"    ") for bookmark in netscape_data.bookmarks]
    for sub_folder in netscape_data.sub_folders:
        export_netscape_data(doc, sub_folder, indent+"    ")
    doc.append(f'{indent}</DL><p>')


def append_header(doc: BookmarkDocument):
    doc.append('<!DOCTYPE NETSCAPE-Bookmark-file-1>')
    doc.append('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">')
    doc.append('<TITLE>Bookmarks</TITLE>')
    doc.append('<H1>Bookmarks</H1>')


def append_bookmark(doc: BookmarkDocument, bookmark: Bookmark, indent: str = ''):
    url = bookmark.url
    title = bookmark.resolved_title
    desc = bookmark.resolved_description
    tags = ','.join(bookmark.tag_names)
    toread = '1' if bookmark.unread else '0'
    added = int(bookmark.date_added.timestamp())

    doc.append(f'{indent}<DT><A HREF="{url}" ADD_DATE="{added}" PRIVATE="0" TOREAD="{toread}" TAGS="{tags}">{title}</A>')

    if desc:
        doc.append(f'{indent}<DD>{desc}')
