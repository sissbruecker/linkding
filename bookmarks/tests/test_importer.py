from django.test import TestCase

from bookmarks.services.importer import import_netscape_html
from bookmarks.tests.helpers import BookmarkFactoryMixin, disable_logging


class ImporterTestCase(TestCase, BookmarkFactoryMixin):

    def create_import_html(self, bookmark_tags_string: str):
        return f'''
<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
{bookmark_tags_string}
</DL><p>
        '''

    @disable_logging
    def test_validate_empty_or_missing_bookmark_url(self):
        test_html = self.create_import_html(f'''
            <!-- Empty URL -->
            <DT><A HREF="" ADD_DATE="1616337559" PRIVATE="0" TOREAD="0" TAGS="tag3">Empty URL</A>
            <DD>Empty URL
            <!-- Missing URL -->
            <DT><A ADD_DATE="1616337559" PRIVATE="0" TOREAD="0" TAGS="tag3">Missing URL</A>
            <DD>Missing URL
        ''')

        import_result = import_netscape_html(test_html, self.get_or_create_test_user())

        self.assertEqual(import_result.success, 0)
