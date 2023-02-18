from django.test import TestCase

from bookmarks.services import exporter
from bookmarks.tests.helpers import BookmarkFactoryMixin


class ExporterTestCase(TestCase, BookmarkFactoryMixin):
    def test_escape_html_in_title_and_description(self):
        bookmark = self.setup_bookmark(
            title='<style>: The Style Information element',
            description='The <style> HTML element contains style information for a document, or part of a document.'
        )
        html = exporter.export_netscape_html([bookmark])

        self.assertIn('&lt;style&gt;: The Style Information element', html)
        self.assertIn(
            'The &lt;style&gt; HTML element contains style information for a document, or part of a document.',
            html
        )

    def test_handle_empty_values(self):
        bookmark = self.setup_bookmark()
        bookmark.title = ''
        bookmark.description = ''
        bookmark.website_title = None
        bookmark.website_description = None
        bookmark.save()
        exporter.export_netscape_html([bookmark])
