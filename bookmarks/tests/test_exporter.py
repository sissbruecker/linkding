from datetime import datetime, timezone

from django.test import TestCase

from bookmarks.services import exporter
from bookmarks.tests.helpers import BookmarkFactoryMixin


class ExporterTestCase(TestCase, BookmarkFactoryMixin):
    def test_export_bookmarks(self):
        bookmarks = [
            self.setup_bookmark(
                url="https://example.com/1",
                title="Title 1",
                added=datetime.fromtimestamp(1, timezone.utc),
                modified=datetime.fromtimestamp(11, timezone.utc),
                description="Example description",
            ),
            self.setup_bookmark(
                url="https://example.com/2",
                title="Title 2",
                added=datetime.fromtimestamp(2, timezone.utc),
                modified=datetime.fromtimestamp(22, timezone.utc),
                tags=[
                    self.setup_tag(name="tag1"),
                    self.setup_tag(name="tag2"),
                    self.setup_tag(name="tag3"),
                ],
            ),
            self.setup_bookmark(
                url="https://example.com/3",
                title="Title 3",
                added=datetime.fromtimestamp(3, timezone.utc),
                modified=datetime.fromtimestamp(33, timezone.utc),
                unread=True,
            ),
            self.setup_bookmark(
                url="https://example.com/4",
                title="Title 4",
                added=datetime.fromtimestamp(4, timezone.utc),
                modified=datetime.fromtimestamp(44, timezone.utc),
                shared=True,
            ),
            self.setup_bookmark(
                url="https://example.com/5",
                title="Title 5",
                added=datetime.fromtimestamp(5, timezone.utc),
                modified=datetime.fromtimestamp(55, timezone.utc),
                shared=True,
                description="Example description",
                notes="Example notes",
            ),
            self.setup_bookmark(
                url="https://example.com/6",
                title="Title 6",
                added=datetime.fromtimestamp(6, timezone.utc),
                modified=datetime.fromtimestamp(66, timezone.utc),
                shared=True,
                notes="Example notes",
            ),
            self.setup_bookmark(
                url="https://example.com/7",
                title="Title 7",
                added=datetime.fromtimestamp(7, timezone.utc),
                modified=datetime.fromtimestamp(77, timezone.utc),
                is_archived=True,
            ),
            self.setup_bookmark(
                url="https://example.com/8",
                title="Title 8",
                added=datetime.fromtimestamp(8, timezone.utc),
                modified=datetime.fromtimestamp(88, timezone.utc),
                tags=[self.setup_tag(name="tag4"), self.setup_tag(name="tag5")],
                is_archived=True,
            ),
        ]
        html = exporter.export_netscape_html(bookmarks)

        lines = [
            '<DT><A HREF="https://example.com/1" ADD_DATE="1" LAST_MODIFIED="11" PRIVATE="1" TOREAD="0" TAGS="">Title 1</A>',
            "<DD>Example description",
            '<DT><A HREF="https://example.com/2" ADD_DATE="2" LAST_MODIFIED="22" PRIVATE="1" TOREAD="0" TAGS="tag1,tag2,tag3">Title 2</A>',
            '<DT><A HREF="https://example.com/3" ADD_DATE="3" LAST_MODIFIED="33" PRIVATE="1" TOREAD="1" TAGS="">Title 3</A>',
            '<DT><A HREF="https://example.com/4" ADD_DATE="4" LAST_MODIFIED="44" PRIVATE="0" TOREAD="0" TAGS="">Title 4</A>',
            '<DT><A HREF="https://example.com/5" ADD_DATE="5" LAST_MODIFIED="55" PRIVATE="0" TOREAD="0" TAGS="">Title 5</A>',
            "<DD>Example description[linkding-notes]Example notes[/linkding-notes]",
            '<DT><A HREF="https://example.com/6" ADD_DATE="6" LAST_MODIFIED="66" PRIVATE="0" TOREAD="0" TAGS="">Title 6</A>',
            "<DD>[linkding-notes]Example notes[/linkding-notes]",
            '<DT><A HREF="https://example.com/7" ADD_DATE="7" LAST_MODIFIED="77" PRIVATE="1" TOREAD="0" TAGS="linkding:archived">Title 7</A>',
            '<DT><A HREF="https://example.com/8" ADD_DATE="8" LAST_MODIFIED="88" PRIVATE="1" TOREAD="0" TAGS="tag4,tag5,linkding:archived">Title 8</A>',
        ]
        self.assertIn("\n\r".join(lines), html)

    def test_escape_html(self):
        bookmark = self.setup_bookmark(
            title="<style>: The Style Information element",
            description="The <style> HTML element contains style information for a document, or part of a document.",
            notes="Interesting notes about the <style> HTML element.",
        )
        html = exporter.export_netscape_html([bookmark])

        self.assertIn("&lt;style&gt;: The Style Information element", html)
        self.assertIn(
            "The &lt;style&gt; HTML element contains style information for a document, or part of a document.",
            html,
        )
        self.assertIn("Interesting notes about the &lt;style&gt; HTML element.", html)

    def test_handle_empty_values(self):
        bookmark = self.setup_bookmark()
        bookmark.title = ""
        bookmark.description = ""
        bookmark.save()
        exporter.export_netscape_html([bookmark])
