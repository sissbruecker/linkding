from typing import List
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from bookmarks.models import Bookmark, Tag, parse_tag_string
from bookmarks.services import tasks
from bookmarks.services.importer import import_netscape_html, ImportOptions
from bookmarks.tests.helpers import (
    BookmarkFactoryMixin,
    ImportTestMixin,
    BookmarkHtmlTag,
    disable_logging,
)
from bookmarks.utils import parse_timestamp


class ImporterTestCase(TestCase, BookmarkFactoryMixin, ImportTestMixin):

    def assertBookmarksImported(self, html_tags: List[BookmarkHtmlTag]):
        for html_tag in html_tags:
            bookmark = Bookmark.objects.get(url=html_tag.href)
            self.assertIsNotNone(bookmark)

            self.assertEqual(bookmark.title, html_tag.title)
            self.assertEqual(bookmark.description, html_tag.description)
            self.assertEqual(bookmark.date_added, parse_timestamp(html_tag.add_date))
            self.assertEqual(
                bookmark.date_modified, parse_timestamp(html_tag.last_modified)
            )
            self.assertEqual(bookmark.unread, html_tag.to_read)
            self.assertEqual(bookmark.shared, not html_tag.private)

            tag_names = parse_tag_string(html_tag.tags)

            # Check assigned tags
            for tag_name in tag_names:
                tag = next(
                    (tag for tag in bookmark.tags.all() if tag.name == tag_name), None
                )
                self.assertIsNotNone(tag)

    def test_import(self):
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
                last_modified="44",
                to_read=True,
            ),
        ]
        import_html = self.render_html(tags=html_tags)
        result = import_netscape_html(import_html, self.get_or_create_test_user())

        # Check result
        self.assertEqual(result.total, 4)
        self.assertEqual(result.success, 4)
        self.assertEqual(result.failed, 0)

        # Check bookmarks
        bookmarks = Bookmark.objects.all()
        self.assertEqual(len(bookmarks), 4)
        self.assertBookmarksImported(html_tags)

    def test_synchronize(self):
        # Initial import
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
                href="https://example.com/unread",
                title="Unread title",
                description="Unread description",
                add_date="4",
                last_modified="44",
                to_read=True,
            ),
            BookmarkHtmlTag(
                href="https://example.com/private",
                title="Private title",
                description="Private description",
                add_date="5",
                last_modified="55",
                private=True,
            ),
        ]
        import_html = self.render_html(tags=html_tags)
        import_netscape_html(import_html, self.get_or_create_test_user())

        # Check bookmarks
        bookmarks = Bookmark.objects.all()
        self.assertEqual(len(bookmarks), 5)
        self.assertBookmarksImported(html_tags)

        # Change data, add some new data
        html_tags = [
            BookmarkHtmlTag(
                href="https://example.com",
                title="Updated Example title",
                description="Updated Example description",
                add_date="111",
                last_modified="1111",
                tags="updated-example-tag",
            ),
            BookmarkHtmlTag(
                href="https://example.com/foo",
                title="Updated Foo title",
                description="Updated Foo description",
                add_date="222",
                last_modified="2222",
                tags="new-tag",
            ),
            BookmarkHtmlTag(
                href="https://example.com/bar",
                title="Updated Bar title",
                description="Updated Bar description",
                add_date="333",
                last_modified="3333",
                tags="updated-bar-tag, updated-other-tag",
            ),
            BookmarkHtmlTag(
                href="https://example.com/unread",
                title="Unread title",
                description="Unread description",
                add_date="3",
                last_modified="3",
                to_read=False,
            ),
            BookmarkHtmlTag(
                href="https://example.com/private",
                title="Private title",
                description="Private description",
                add_date="4",
                last_modified="4",
                private=False,
            ),
            BookmarkHtmlTag(
                href="https://baz.com",
                add_date="444",
                last_modified="4444",
                tags="baz-tag",
            ),
        ]

        # Import updated data
        import_html = self.render_html(tags=html_tags)
        result = import_netscape_html(
            import_html,
            self.get_or_create_test_user(),
            ImportOptions(map_private_flag=True),
        )

        # Check result
        self.assertEqual(result.total, 6)
        self.assertEqual(result.success, 6)
        self.assertEqual(result.failed, 0)

        # Check bookmarks
        bookmarks = Bookmark.objects.all()
        self.assertEqual(len(bookmarks), 6)
        self.assertBookmarksImported(html_tags)

    def test_import_with_some_invalid_bookmarks(self):
        html_tags = [
            BookmarkHtmlTag(href="https://example.com"),
            # Invalid URL
            BookmarkHtmlTag(href="foo.com"),
            # No URL
            BookmarkHtmlTag(),
        ]
        import_html = self.render_html(tags=html_tags)
        result = import_netscape_html(import_html, self.get_or_create_test_user())

        # Check result
        self.assertEqual(result.total, 3)
        self.assertEqual(result.success, 1)
        self.assertEqual(result.failed, 2)

        # Check bookmarks
        bookmarks = Bookmark.objects.all()
        self.assertEqual(len(bookmarks), 1)
        self.assertBookmarksImported(html_tags[1:1])

    def test_import_invalid_bookmark_does_not_associate_tags(self):
        html_tags = [
            # No URL
            BookmarkHtmlTag(tags="tag1, tag2, tag3"),
        ]
        import_html = self.render_html(tags=html_tags)
        # Sqlite silently ignores relationships that have a non-persisted bookmark,
        # thus testing if the bulk create receives no relationships
        BookmarkToTagRelationShip = Bookmark.tags.through
        with patch.object(
            BookmarkToTagRelationShip.objects, "bulk_create"
        ) as mock_bulk_create:
            import_netscape_html(import_html, self.get_or_create_test_user())
            mock_bulk_create.assert_called_once_with([], ignore_conflicts=True)

    def test_import_tags(self):
        html_tags = [
            BookmarkHtmlTag(href="https://example.com", tags="tag1"),
            BookmarkHtmlTag(href="https://foo.com", tags="tag2"),
            BookmarkHtmlTag(href="https://bar.com", tags="tag3"),
        ]
        import_html = self.render_html(tags=html_tags)
        import_netscape_html(import_html, self.get_or_create_test_user())

        self.assertEqual(Tag.objects.count(), 3)

    def test_create_missing_tags(self):
        html_tags = [
            BookmarkHtmlTag(href="https://example.com", tags="tag1"),
            BookmarkHtmlTag(href="https://foo.com", tags="tag2"),
            BookmarkHtmlTag(href="https://bar.com", tags="tag3"),
        ]
        import_html = self.render_html(tags=html_tags)
        import_netscape_html(import_html, self.get_or_create_test_user())

        html_tags.append(BookmarkHtmlTag(href="https://baz.com", tags="tag4"))
        import_html = self.render_html(tags=html_tags)
        import_netscape_html(import_html, self.get_or_create_test_user())

        self.assertEqual(Tag.objects.count(), 4)

    def test_create_missing_tags_does_not_duplicate_tags(self):
        html_tags = [
            BookmarkHtmlTag(href="https://example.com", tags="tag1"),
            BookmarkHtmlTag(href="https://foo.com", tags="tag1"),
            BookmarkHtmlTag(href="https://bar.com", tags="tag1"),
        ]
        import_html = self.render_html(tags=html_tags)
        import_netscape_html(import_html, self.get_or_create_test_user())

        self.assertEqual(Tag.objects.count(), 1)

    def test_should_append_tags_to_bookmark_when_reimporting_with_different_tags(self):
        html_tags = [
            BookmarkHtmlTag(href="https://example.com", tags="tag1"),
        ]
        import_html = self.render_html(tags=html_tags)
        import_netscape_html(import_html, self.get_or_create_test_user())

        html_tags.append(BookmarkHtmlTag(href="https://example.com", tags="tag2, tag3"))
        import_html = self.render_html(tags=html_tags)
        import_netscape_html(import_html, self.get_or_create_test_user())

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(Bookmark.objects.all()[0].tags.all().count(), 3)

    @override_settings(USE_TZ=False)
    def test_use_current_date_when_no_add_date(self):
        test_html = self.render_html(
            tags_html=f"""
            <DT><A HREF="https://example.com">Example.com</A>
            <DD>Example.com
        """
        )

        with patch.object(timezone, "now", return_value=timezone.datetime(2021, 1, 1)):
            import_netscape_html(test_html, self.get_or_create_test_user())

            self.assertEqual(Bookmark.objects.count(), 1)
            self.assertEqual(
                Bookmark.objects.all()[0].date_added, timezone.datetime(2021, 1, 1)
            )

    def test_use_add_date_when_no_last_modified(self):
        test_html = self.render_html(
            tags_html=f"""
            <DT><A HREF="https://example.com" ADD_DATE="1">Example.com</A>
            <DD>Example.com
        """
        )

        import_netscape_html(test_html, self.get_or_create_test_user())

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(Bookmark.objects.all()[0].date_modified, parse_timestamp("1"))

    def test_keep_title_if_imported_bookmark_has_empty_title(self):
        test_html = self.render_html(
            tags=[BookmarkHtmlTag(href="https://example.com", title="Example.com")]
        )
        import_netscape_html(test_html, self.get_or_create_test_user())

        test_html = self.render_html(tags=[BookmarkHtmlTag(href="https://example.com")])
        import_netscape_html(test_html, self.get_or_create_test_user())

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(Bookmark.objects.all()[0].title, "Example.com")

    def test_keep_description_if_imported_bookmark_has_empty_description(self):
        test_html = self.render_html(
            tags=[
                BookmarkHtmlTag(href="https://example.com", description="Example.com")
            ]
        )
        import_netscape_html(test_html, self.get_or_create_test_user())

        test_html = self.render_html(tags=[BookmarkHtmlTag(href="https://example.com")])
        import_netscape_html(test_html, self.get_or_create_test_user())

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(Bookmark.objects.all()[0].description, "Example.com")

    def test_replace_whitespace_in_tag_names(self):
        test_html = self.render_html(
            tags_html=f"""
            <DT><A HREF="https://example.com" TAGS="tag 1, tag 2, tag 3">Example.com</A>
            <DD>Example.com
        """
        )
        import_netscape_html(test_html, self.get_or_create_test_user())

        tags = Tag.objects.all()
        tag_names = [tag.name for tag in tags]

        self.assertListEqual(tag_names, ["tag-1", "tag-2", "tag-3"])

    @disable_logging
    def test_validate_empty_or_missing_bookmark_url(self):
        test_html = self.render_html(
            tags_html=f"""
            <DT><A HREF="">Empty URL</A>
            <DD>Empty URL
            <DT><A>Missing URL</A>
            <DD>Missing URL
        """
        )

        import_result = import_netscape_html(test_html, self.get_or_create_test_user())

        self.assertEqual(Bookmark.objects.count(), 0)
        self.assertEqual(import_result.success, 0)
        self.assertEqual(import_result.failed, 2)

    def test_private_flag(self):
        # does not map private flag if not enabled in options
        test_html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com/1" ADD_DATE="1">Example title 1</A>
        <DD>Example description 1</DD>
        <DT><A HREF="https://example.com/2" ADD_DATE="1" PRIVATE="1">Example title 2</A>
        <DD>Example description 2</DD>
        <DT><A HREF="https://example.com/3" ADD_DATE="1" PRIVATE="0">Example title 3</A>
        <DD>Example description 3</DD>
        """
        )
        import_netscape_html(test_html, self.get_or_create_test_user(), ImportOptions())

        self.assertEqual(Bookmark.objects.count(), 3)
        self.assertEqual(Bookmark.objects.all()[0].shared, False)
        self.assertEqual(Bookmark.objects.all()[1].shared, False)
        self.assertEqual(Bookmark.objects.all()[2].shared, False)

        # does map private flag if enabled in options
        Bookmark.objects.all().delete()
        import_netscape_html(
            test_html,
            self.get_or_create_test_user(),
            ImportOptions(map_private_flag=True),
        )
        bookmark1 = Bookmark.objects.get(url="https://example.com/1")
        bookmark2 = Bookmark.objects.get(url="https://example.com/2")
        bookmark3 = Bookmark.objects.get(url="https://example.com/3")
        self.assertEqual(bookmark1.shared, False)
        self.assertEqual(bookmark2.shared, False)
        self.assertEqual(bookmark3.shared, True)

    def test_archived_state(self):
        test_html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com/1" ADD_DATE="1" TAGS="tag1,tag2,linkding:archived">Example title 1</A>
        <DD>Example description 1</DD>
        <DT><A HREF="https://example.com/2" ADD_DATE="1" PRIVATE="1" TAGS="tag1,tag2">Example title 2</A>
        <DD>Example description 2</DD>
        <DT><A HREF="https://example.com/3" ADD_DATE="1" PRIVATE="0">Example title 3</A>
        <DD>Example description 3</DD>
        """
        )
        import_netscape_html(test_html, self.get_or_create_test_user(), ImportOptions())

        self.assertEqual(Bookmark.objects.count(), 3)
        self.assertEqual(Bookmark.objects.all()[0].is_archived, True)
        self.assertEqual(Bookmark.objects.all()[1].is_archived, False)
        self.assertEqual(Bookmark.objects.all()[2].is_archived, False)

        tags = Tag.objects.all()
        self.assertEqual(len(tags), 2)
        self.assertEqual(tags[0].name, "tag1")
        self.assertEqual(tags[1].name, "tag2")

    def test_notes(self):
        # initial notes
        test_html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        <DD>Example description[linkding-notes]Example notes[/linkding-notes]
        """
        )
        import_netscape_html(test_html, self.get_or_create_test_user(), ImportOptions())

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(Bookmark.objects.all()[0].description, "Example description")
        self.assertEqual(Bookmark.objects.all()[0].notes, "Example notes")

        # update notes
        test_html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        <DD>Example description[linkding-notes]Updated notes[/linkding-notes]
        """
        )
        import_netscape_html(test_html, self.get_or_create_test_user(), ImportOptions())

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(Bookmark.objects.all()[0].description, "Example description")
        self.assertEqual(Bookmark.objects.all()[0].notes, "Updated notes")

        # does not override existing notes if empty
        test_html = self.render_html(
            tags_html="""
        <DT><A HREF="https://example.com" ADD_DATE="1">Example title</A>
        <DD>Example description
        """
        )
        import_netscape_html(test_html, self.get_or_create_test_user(), ImportOptions())

        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(Bookmark.objects.all()[0].description, "Example description")
        self.assertEqual(Bookmark.objects.all()[0].notes, "Updated notes")

    def test_schedule_favicon_loading(self):
        user = self.get_or_create_test_user()
        test_html = self.render_html(tags_html="")

        with patch.object(
            tasks, "schedule_bookmarks_without_favicons"
        ) as mock_schedule_bookmarks_without_favicons:
            import_netscape_html(test_html, user)

            mock_schedule_bookmarks_without_favicons.assert_called_once_with(user)

    def test_schedule_preview_loading(self):
        user = self.get_or_create_test_user()
        test_html = self.render_html(tags_html="")

        with patch.object(
            tasks, "schedule_bookmarks_without_previews"
        ) as mock_schedule_bookmarks_without_previews:
            import_netscape_html(test_html, user)

            mock_schedule_bookmarks_without_previews.assert_called_once_with(user)
