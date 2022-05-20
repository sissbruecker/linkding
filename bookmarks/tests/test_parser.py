from dataclasses import dataclass
from typing import List, Optional

from django.test import TestCase

from bookmarks.services.parser import parse
from services.parser import NetscapeBookmark


@dataclass
class BookmarkTagData:
    href: Optional[str]
    title: Optional[str]
    description: Optional[str]
    add_date: Optional[str]
    tags: Optional[str]


def render_tag(tag: BookmarkTagData):
    return f'''
    <DT>
    <A {f'HREF="{tag.href}"' if tag.href else ''}
       {f'ADD_DATE="{tag.add_date}"' if tag.add_date else ''}
       {f'TAGS="{tag.tags}"' if tag.tags else ''}>
       {tag.title if tag.title else ''}
    </A>
    {f'<DD>{tag.description}' if tag.description else ''}
    '''


def render_html(tags: List[BookmarkTagData] = None, tags_html: str = ''):
    if tags:
        rendered_tags = [render_tag(tag) for tag in tags]
        tags_html = '\n'.join(rendered_tags)
    return f'''
    <!DOCTYPE NETSCAPE-Bookmark-file-1>
    <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
    <TITLE>Bookmarks</TITLE>
    <H1>Bookmarks</H1>
    <DL><p>
    {tags_html}
    </DL><p>
    '''


class ParserTestCase(TestCase):
    def assertTagsEqual(self, bookmarks: List[NetscapeBookmark], tags: List[BookmarkTagData]):
        self.assertEqual(len(bookmarks), len(tags))
        for bookmark in bookmarks:
            tag = tags[bookmarks.index(bookmark)]
            self.assertEqual(bookmark.href, tag.href)
            self.assertEqual(bookmark.title, tag.title)
            self.assertEqual(bookmark.date_added, tag.add_date)
            self.assertEqual(bookmark.description, tag.description)
            self.assertEqual(bookmark.tag_string, tag.tags)

    def test_parse_bookmarks(self):
        tags = [
            BookmarkTagData(href='https://example.com', title='Example title', description='Example description',
                            add_date='1', tags='example-tag'),
            BookmarkTagData(href='https://foo.com', title='Foo title', description='',
                            add_date='2', tags=''),
            BookmarkTagData(href='https://bar.com', title='Bar title', description='Bar description',
                            add_date='3', tags='bar-tag, other-tag'),
        ]
        html = render_html(tags)
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, tags)

    def test_no_bookmarks(self):
        html = render_html()
        bookmarks = parse(html)

        self.assertEqual(bookmarks, [])

    def test_reset_properties_after_adding_tag(self):
        tags = [
            BookmarkTagData(href='https://example.com', title='Example title', description='Example description',
                            add_date='1', tags='example-tag'),
            BookmarkTagData(href='', title='', description='',
                            add_date='', tags='')
        ]
        html = render_html(tags)
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, tags)

    def test_empty_title(self):
        tags = [
            BookmarkTagData(href='https://example.com', title='', description='Example description',
                            add_date='1', tags='example-tag'),
        ]
        html = render_html(tags_html='''
        <DT><A HREF="https://example.com" ADD_DATE="1" TAGS="example-tag"></A>
        <DD>Example description
        ''')
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, tags)

    def test_with_closing_description_tag(self):
        tags = [
            BookmarkTagData(href='https://example.com', title='Example title', description='Example description',
                            add_date='1', tags='example-tag'),
            BookmarkTagData(href='https://foo.com', title='Foo title', description='',
                            add_date='2', tags=''),
        ]
        html = render_html(tags_html='''
        <DT><A HREF="https://example.com" ADD_DATE="1" TAGS="example-tag">Example title</A>
        <DD>Example description</DD>
        <DT><A HREF="https://foo.com" ADD_DATE="2">Foo title</A>
        <DD></DD>
        ''')
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, tags)

    def test_description_tag_before_anchor_tag(self):
        tags = [
            BookmarkTagData(href='https://example.com', title='Example title', description='Example description',
                            add_date='1', tags='example-tag'),
            BookmarkTagData(href='https://foo.com', title='Foo title', description='',
                            add_date='2', tags=''),
        ]
        html = render_html(tags_html='''
        <DT><DD>Example description</DD>
        <A HREF="https://example.com" ADD_DATE="1" TAGS="example-tag">Example title</A>
        <DT><DD></DD>
        <A HREF="https://foo.com" ADD_DATE="2">Foo title</A>
        ''')
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, tags)

    def test_with_folders(self):
        tags = [
            BookmarkTagData(href='https://example.com', title='Example title', description='Example description',
                            add_date='1', tags='example-tag'),
            BookmarkTagData(href='https://foo.com', title='Foo title', description='',
                            add_date='2', tags=''),
        ]
        html = render_html(tags_html='''
        <DL><p>
            <DT><H3>Folder 1</H3>
            <DL><p>
                <DT><A HREF="https://example.com" ADD_DATE="1" TAGS="example-tag">Example title</A>
                <DD>Example description
            </DL><p>
            <DT><H3>Folder 2</H3>
            <DL><p>
                <DT><A HREF="https://foo.com" ADD_DATE="2">Foo title</A>
            </DL><p>
        </DL><p>
        ''')
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, tags)