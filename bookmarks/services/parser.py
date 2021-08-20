from dataclasses import dataclass
from typing import Type

import pyparsing as pp


@dataclass
class NetscapeBookmark:
    href: str
    title: str
    description: str
    date_added: str
    tag_string: str

@dataclass
class NetscapeBookmarkFileData:
    folder: str
    bookmarks: [NetscapeBookmark]
    sub_folders: [Type['NetscapeBookmarkFileData']]


def extract_bookmark(tokens):
    bookmark = tokens.link
    if tokens.description:
        bookmark.description = tokens.description[0]
    return {'type': "bookmark",
            'data': bookmark,
            }

def extract_folder_data(tokens):
    bookmarks = []
    sub_folders = []
    for elem in tokens.folder_items:
        if elem['type'] == "bookmark":
            bookmarks.append(elem['data'])
        else:
            sub_folders.append(elem['data'])
    return NetscapeBookmarkFileData(folder='',
                                    bookmarks=bookmarks,
                                    sub_folders=sub_folders,
                                    )


# define grammar
dt_start, _ = pp.makeHTMLTags("DT")
dd_start, _ = pp.makeHTMLTags("DD")
a_start, a_end = pp.makeHTMLTags("A")
bookmark_link = a_start + a_start.tag_body("text") + a_end
bookmark_link.setParseAction(lambda tokens: NetscapeBookmark(href=tokens.href,
                                                             title=tokens.text,
                                                             description='',
                                                             tag_string=tokens.tags,
                                                             date_added=tokens.add_date,
                                                             ))

bookmark_description = dd_start + pp.SkipTo(pp.anyOpenTag | pp.anyCloseTag)("description")
bookmark_description.setParseAction(lambda tokens: tokens.description.strip())

bookmark = dt_start + bookmark_link("link") + pp.ZeroOrMore(bookmark_description)("description")
bookmark.setParseAction(extract_bookmark)

p_start, _ = pp.makeHTMLTags("p")
dl_start, dl_end = pp.makeHTMLTags("DL")
folder = pp.Forward()
folder_data = dl_start + p_start + pp.Group(pp.ZeroOrMore(bookmark | folder))("folder_items") + dl_end + pp.Optional(p_start)
folder_data.setParseAction(extract_folder_data)

h3_start, h3_end = pp.makeHTMLTags("H3")
folder_name = h3_start + h3_start.tag_body("text") + h3_end
folder_name.setParseAction(lambda tokens: tokens.text)

folder << dt_start + folder_name("folder_name") + folder_data("data")
folder.setParseAction(lambda tokens: {'type': "folder",
                                      'data': NetscapeBookmarkFileData(
                                          folder=tokens.folder_name,
                                          bookmarks=tokens.data.bookmarks,
                                          sub_folders=tokens.data.sub_folders,
                                      )})


def parse(html: str):
    bookmarks_data = folder_data.searchString(html)[0][0]

    return bookmarks_data
