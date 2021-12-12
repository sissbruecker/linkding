from unittest.mock import patch

from django.test import TestCase

from bookmarks.models import Tag
from bookmarks.services import tasks
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

    def test_replace_whitespace_in_tag_names(self):
        test_html = self.create_import_html(f'''
            <DT><A HREF="https://example.com" ADD_DATE="1616337559" PRIVATE="0" TOREAD="0" TAGS="tag 1, tag 2, tag 3">Example.com</A>
            <DD>Example.com
        ''')
        import_netscape_html(test_html, self.get_or_create_test_user())

        tags = Tag.objects.all()
        tag_names = [tag.name for tag in tags]

        self.assertListEqual(tag_names, ['tag-1', 'tag-2', 'tag-3'])

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

    def test_schedule_snapshot_creation(self):
        user = self.get_or_create_test_user()
        test_html = self.create_import_html('')

        with patch.object(tasks, 'schedule_bookmarks_without_snapshots') as mock_schedule_bookmarks_without_snapshots:
            import_netscape_html(test_html, user)

            mock_schedule_bookmarks_without_snapshots.assert_called_once_with(user.id)
