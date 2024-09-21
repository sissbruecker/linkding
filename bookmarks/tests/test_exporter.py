from django.test import TestCase
from django.utils import timezone

from bookmarks.services import exporter
from bookmarks.tests.helpers import BookmarkFactoryMixin


class ExporterTestCase(TestCase, BookmarkFactoryMixin):
    def test_export_bookmarks(self):
        added = timezone.now()
        timestamp = int(added.timestamp())

        bookmarks = [
            self.setup_bookmark(
                url="https://example.com/1",
                title="Title 1",
                added=added,
                description="Example description",
            ),
            self.setup_bookmark(
                url="https://example.com/2",
                title="Title 2",
                added=added,
                tags=[
                    self.setup_tag(name="tag1"),
                    self.setup_tag(name="tag2"),
                    self.setup_tag(name="tag3"),
                ],
            ),
            self.setup_bookmark(
                url="https://example.com/3", title="Title 3", added=added, unread=True
            ),
            self.setup_bookmark(
                url="https://example.com/4", title="Title 4", added=added, shared=True
            ),
            self.setup_bookmark(
                url="https://example.com/5",
                title="Title 5",
                added=added,
                shared=True,
                description="Example description",
                notes="Example notes",
            ),
            self.setup_bookmark(
                url="https://example.com/6",
                title="Title 6",
                added=added,
                shared=True,
                notes="Example notes",
            ),
            self.setup_bookmark(
                url="https://example.com/7",
                title="Title 7",
                added=added,
                is_archived=True,
            ),
            self.setup_bookmark(
                url="https://example.com/8",
                title="Title 8",
                added=added,
                tags=[self.setup_tag(name="tag4"), self.setup_tag(name="tag5")],
                is_archived=True,
            ),
        ]
        html = exporter.export_netscape_html(bookmarks)

        lines = [
            f'<DT><A HREF="https://example.com/1" ADD_DATE="{timestamp}" PRIVATE="1" TOREAD="0" TAGS="">Title 1</A>',
            "<DD>Example description",
            f'<DT><A HREF="https://example.com/2" ADD_DATE="{timestamp}" PRIVATE="1" TOREAD="0" TAGS="tag1,tag2,tag3">Title 2</A>',
            f'<DT><A HREF="https://example.com/3" ADD_DATE="{timestamp}" PRIVATE="1" TOREAD="1" TAGS="">Title 3</A>',
            f'<DT><A HREF="https://example.com/4" ADD_DATE="{timestamp}" PRIVATE="0" TOREAD="0" TAGS="">Title 4</A>',
            f'<DT><A HREF="https://example.com/5" ADD_DATE="{timestamp}" PRIVATE="0" TOREAD="0" TAGS="">Title 5</A>',
            "<DD>Example description[linkding-notes]Example notes[/linkding-notes]",
            f'<DT><A HREF="https://example.com/6" ADD_DATE="{timestamp}" PRIVATE="0" TOREAD="0" TAGS="">Title 6</A>',
            "<DD>[linkding-notes]Example notes[/linkding-notes]",
            f'<DT><A HREF="https://example.com/7" ADD_DATE="{timestamp}" PRIVATE="1" TOREAD="0" TAGS="linkding:archived">Title 7</A>',
            f'<DT><A HREF="https://example.com/8" ADD_DATE="{timestamp}" PRIVATE="1" TOREAD="0" TAGS="tag4,tag5,linkding:archived">Title 8</A>',
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
