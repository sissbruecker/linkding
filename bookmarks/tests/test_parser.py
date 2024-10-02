from typing import List

from django.test import TestCase

from bookmarks.models import parse_tag_string
from bookmarks.services.parser import NetscapeBookmark
from bookmarks.services.parser import parse
from bookmarks.tests.helpers import ImportTestMixin, BookmarkHtmlTag


class ParserTestCase(TestCase, ImportTestMixin):
    def assertTagsEqual(
        self, bookmarks: List[NetscapeBookmark], html_tags: List[BookmarkHtmlTag]
    ):
        self.assertEqual(len(bookmarks), len(html_tags))
        for bookmark in bookmarks:
            html_tag = html_tags[bookmarks.index(bookmark)]
            self.assertEqual(bookmark.href, html_tag.href)
            self.assertEqual(bookmark.title, html_tag.title)
            self.assertEqual(bookmark.date_added, html_tag.add_date)
            self.assertEqual(bookmark.date_modified, html_tag.last_modified)
            self.assertEqual(bookmark.description, html_tag.description)
            self.assertEqual(bookmark.tag_names, parse_tag_string(html_tag.tags))
            self.assertEqual(bookmark.to_read, html_tag.to_read)
            self.assertEqual(bookmark.private, html_tag.private)

    def test_parse_bookmarks(self):
        html_tags = [
            BookmarkHtmlTag(
                href="https://example.com",
                title="Example title",
                description="Example description",
                add_date="1",
                last_modified="11",
                tags="example-tag",
            ),
            BookmarkHtmlTag(
                href="https://example.com/foo",
                title="Foo title",
                description="",
                add_date="2",
                last_modified="22",
                tags="",
            ),
            BookmarkHtmlTag(
                href="https://example.com/bar",
                title="Bar title",
                description="Bar description",
                add_date="3",
                last_modified="33",
                tags="bar-tag, other-tag",
            ),
            BookmarkHtmlTag(
                href="https://example.com/baz",
                title="Baz title",
                description="Baz description",
                add_date="4",
                to_read=True,
            ),
        ]
        html = self.render_html(html_tags)
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, html_tags)

    def test_no_bookmarks(self):
        html = self.render_html()
        bookmarks = parse(html)

        self.assertEqual(bookmarks, [])

    def test_reset_properties_after_adding_bookmark(self):
        html_tags = [
            BookmarkHtmlTag(
                href="https://example.com",
                title="Example title",
                description="Example description",
                add_date="1",
                last_modified="1",
                tags="example-tag",
            ),
            BookmarkHtmlTag(
                href="",
                title="",
                description="",
                add_date="",
                last_modified="",
                tags="",
            ),
        ]
        html = self.render_html(html_tags)
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, html_tags)

    def test_empty_title(self):
        html_tags = [
            BookmarkHtmlTag(
                href="https://example.com",
                title="",
                description="Example description",
                add_date="1",
                tags="example-tag",
            ),
        ]
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1" TAGS="example-tag"></A>
        <DD>Example description
        """
        )
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, html_tags)

    def test_with_closing_description_tag(self):
        html_tags = [
            BookmarkHtmlTag(
                href="https://example.com",
                title="Example title",
                description="Example description",
                add_date="1",
                tags="example-tag",
            ),
            BookmarkHtmlTag(
                href="https://foo.com",
                title="Foo title",
                description="",
                add_date="2",
                tags="",
            ),
        ]
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1" TAGS="example-tag">Example title</A>
        <DD>Example description</DD>
        <DT><A HREF="https://foo.com" ADD_DATE="2">Foo title</A>
        <DD></DD>
        """
        )
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, html_tags)

    def test_description_tag_before_anchor_tag(self):
        html_tags = [
            BookmarkHtmlTag(
                href="https://example.com",
                title="Example title",
                description="Example description",
                add_date="1",
                tags="example-tag",
            ),
            BookmarkHtmlTag(
                href="https://foo.com",
                title="Foo title",
                description="",
                add_date="2",
                tags="",
            ),
        ]
        html = self.render_html(
            tags_html="""
        <DT><DD>Example description</DD>
        <A HREF="https://example.com" ADD_DATE="1" TAGS="example-tag">Example title</A>
        <DT><DD></DD>
        <A HREF="https://foo.com" ADD_DATE="2">Foo title</A>
        """
        )
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, html_tags)

    def test_with_folders(self):
        html_tags = [
            BookmarkHtmlTag(
                href="https://example.com",
                title="Example title",
                description="Example description",
                add_date="1",
                tags="example-tag",
            ),
            BookmarkHtmlTag(
                href="https://foo.com",
                title="Foo title",
                description="",
                add_date="2",
                tags="",
            ),
        ]
        html = self.render_html(
            tags_html="""
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
        """
        )
        bookmarks = parse(html)

        self.assertTagsEqual(bookmarks, html_tags)

    def test_private_flag(self):
        # is private by default
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        <DD>Example description</DD>
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].private, True)

        # explicitly marked as private
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1" PRIVATE="1">Example title</A>
        <DD>Example description</DD>
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].private, True)

        # explicitly marked as public
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1" PRIVATE="0">Example title</A>
        <DD>Example description</DD>
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].private, False)

    def test_notes(self):
        # no description, no notes
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].description, "")
        self.assertEqual(bookmarks[0].notes, "")

        # description, no notes
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        <DD>Example description
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].description, "Example description")
        self.assertEqual(bookmarks[0].notes, "")

        # description, notes
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        <DD>Example description[linkding-notes]Example notes[/linkding-notes]
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].description, "Example description")
        self.assertEqual(bookmarks[0].notes, "Example notes")

        # description, notes without closing tag
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        <DD>Example description[linkding-notes]Example notes
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].description, "Example description")
        self.assertEqual(bookmarks[0].notes, "Example notes")

        # no description, notes
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        <DD>[linkding-notes]Example notes[/linkding-notes]
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].description, "")
        self.assertEqual(bookmarks[0].notes, "Example notes")

        # notes reset between bookmarks
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com/1" ADD_DATE="1">Example title</A>
        <DD>[linkding-notes]Example notes[/linkding-notes]
        <DT><A HREF="https://example.com/2" ADD_DATE="1">Example title</A>
        <DD>Example description
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].description, "")
        self.assertEqual(bookmarks[0].notes, "Example notes")
        self.assertEqual(bookmarks[1].description, "Example description")
        self.assertEqual(bookmarks[1].notes, "")

    def test_unescape_content(self):
        html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">&lt;style&gt;: The Style Information element</A>
        <DD>The &lt;style&gt; HTML element contains style information for a document, or part of a document.[linkding-notes]Interesting notes about the &lt;style&gt; HTML element.[/linkding-notes]
        """
        )
        bookmarks = parse(html)
        self.assertEqual(bookmarks[0].title, "<style>: The Style Information element")
        self.assertEqual(
            bookmarks[0].description,
            "The <style> HTML element contains style information for a document, or part of a document.",
        )
        self.assertEqual(
            bookmarks[0].notes, "Interesting notes about the <style> HTML element."
        )
