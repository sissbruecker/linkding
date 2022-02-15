from collections import Counter
from functools import reduce
from itertools import chain
from typing import Dict, List, Union

from bookmarks.models import Bookmark

BookmarkDocument = List[str]
Tree = Dict[Union[str, int], Union[Dict, Bookmark]]


def export_netscape_html(bookmarks: List[Bookmark], apply_pseudo_structure: str):
    doc: BookmarkDocument = []
    if apply_pseudo_structure == 'on':
        append_header(doc)
        append_list_start(doc)
        counter = Counter(chain.from_iterable(frozenset(frozenset(bookmark.tag_names) for bookmark in bookmarks)))
        tree: Tree = {}
        for bookmark in bookmarks:
            path: List[Union[str, Bookmark]] = sorted(bookmark.tag_names, key=lambda c: counter[c], reverse=True) + [bookmark]
            reduce(
                lambda d, k: d.setdefault(len(d), k) if isinstance(k, Bookmark) else d.setdefault(k, {}),
                path,
                tree,
            )
        append_branch(doc, tree)
        append_list_end(doc)
    else:
        [append_bookmark(doc, bookmark) for bookmark in bookmarks]

    return '\n\r'.join(doc)


def append_branch(doc: BookmarkDocument, branch: Tree):
    append_list_start(doc)
    # Folders
    for key, value in branch.items():
        if isinstance(key, str):
            doc.append(f'<DT><H3 ADD_DATE="0" LAST_MODIFIED="0">{key.title()}</H3>')
            append_branch(doc, value)
    # Bookmarks
    for key, value in branch.items():
        if isinstance(value, Bookmark):
            append_bookmark(doc, value)
    append_list_end(doc)


def append_header(doc: BookmarkDocument):
    doc.append('<!DOCTYPE NETSCAPE-Bookmark-file-1>')
    doc.append('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">')
    doc.append('<TITLE>Bookmarks</TITLE>')
    doc.append('<H1>Bookmarks</H1>')


def append_list_start(doc: BookmarkDocument):
    doc.append('<DL><p>')


def append_bookmark(doc: BookmarkDocument, bookmark: Bookmark):
    url = bookmark.url
    title = bookmark.resolved_title
    desc = bookmark.resolved_description
    tags = ','.join(bookmark.tag_names)
    toread = '1' if bookmark.unread else '0'
    added = int(bookmark.date_added.timestamp())

    doc.append(f'<DT><A HREF="{url}" ADD_DATE="{added}" PRIVATE="0" TOREAD="{toread}" TAGS="{tags}">{title}</A>')

    if desc:
        doc.append(f'<DD>{desc}')


def append_list_end(doc: BookmarkDocument):
    doc.append('</DL><p>')
