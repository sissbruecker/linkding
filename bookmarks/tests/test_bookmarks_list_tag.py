from dateutil.relativedelta import relativedelta
from django.core.paginator import Paginator
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone, formats

from bookmarks.models import Bookmark, UserProfile, User
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkListTagTest(TestCase, BookmarkFactoryMixin):

    def assertBookmarksLink(self, html: str, bookmark: Bookmark, link_target: str = '_blank', unread: bool = False):
        self.assertInHTML(
            f'''
            <a href="{bookmark.url}" 
                target="{link_target}" 
                rel="noopener" 
                class="{'text-italic' if unread else ''}">{bookmark.resolved_title}</a>
            ''',
            html
        )

    def assertDateLabel(self, html: str, label_content: str):
        self.assertInHTML(f'''
        <span>
            <span>{label_content}</span>
        </span>
        <span class="separator">|</span>
        ''', html)

    def assertWebArchiveLink(self, html: str, label_content: str, url: str, link_target: str = '_blank'):
        self.assertInHTML(f'''
        <span>
            <a href="{url}"
               title="Show snapshot on the Internet Archive Wayback Machine" target="{link_target}" rel="noopener">
                <span>{label_content}</span>
                ∞
            </a>
        </span>
        <span class="separator">|</span>
        ''', html)

    def assertBookmarkActions(self, html: str, bookmark: Bookmark):
        self.assertBookmarkActionsCount(html, bookmark, count=1)

    def assertNoBookmarkActions(self, html: str, bookmark: Bookmark):
        self.assertBookmarkActionsCount(html, bookmark, count=0)

    def assertBookmarkActionsCount(self, html: str, bookmark: Bookmark, count=1):
        # Edit link
        edit_url = reverse('bookmarks:edit', args=[bookmark.id])
        self.assertInHTML(f'''
            <a href="{edit_url}?return_url=/test">Edit</a>
        ''', html, count=count)
        # Archive link
        self.assertInHTML(f'''
            <button type="submit" name="archive" value="{bookmark.id}"
               class="btn btn-link btn-sm">Archive</button>
        ''', html, count=count)
        # Delete link
        self.assertInHTML(f'''
            <button type="submit" name="remove" value="{bookmark.id}"
               class="btn btn-link btn-sm btn-confirmation">Remove</button>
        ''', html, count=count)

    def assertShareInfo(self, html: str, bookmark: Bookmark):
        self.assertShareInfoCount(html, bookmark, 1)

    def assertNoShareInfo(self, html: str, bookmark: Bookmark):
        self.assertShareInfoCount(html, bookmark, 0)

    def assertShareInfoCount(self, html: str, bookmark: Bookmark, count=1):
        self.assertInHTML(f'''
            <span>Shared by 
                <a href="?user={bookmark.owner.username}">{bookmark.owner.username}</a>
            </span>
        ''', html, count=count)

    def assertFaviconVisible(self, html: str, bookmark: Bookmark):
        self.assertFaviconCount(html, bookmark, 1)

    def assertFaviconHidden(self, html: str, bookmark: Bookmark):
        self.assertFaviconCount(html, bookmark, 0)

    def assertFaviconCount(self, html: str, bookmark: Bookmark, count=1):
        self.assertInHTML(f'''
            <img src="/static/{bookmark.favicon_file}" alt="">
            ''', html, count=count)

    def assertBookmarkURLCount(self, html: str, bookmark: Bookmark, link_target: str = '_blank', count=0):
        self.assertInHTML(f'''
        <div class="url-path truncate">
          <a href="{bookmark.url}" target="{link_target}" rel="noopener" 
          class="url-display text-sm">
            {bookmark.url}
          </a>
        </div>
        ''', html, count)

    def assertBookmarkURLVisible(self, html: str, bookmark: Bookmark):
        self.assertBookmarkURLCount(html, bookmark, count=1)

    def assertBookmarkURLHidden(self, html: str, bookmark: Bookmark, link_target: str = '_blank'):
        self.assertBookmarkURLCount(html, bookmark, count=0)

    def assertNotes(self, html: str, notes_html: str, count=1):
        self.assertInHTML(f'''
        <div class="notes bg-gray text-gray-dark">
          <div class="notes-content">
            {notes_html}
          </div>
        </div>
        ''', html, count=count)

    def assertNotesToggle(self, html: str, count=1):
        self.assertInHTML(f'''
          <button class="btn btn-link btn-sm toggle-notes" title="Toggle notes">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-notes" width="16" height="16"
                 viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
                 stroke-linejoin="round">
              <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
              <path d="M5 3m0 2a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v14a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2z"></path>
              <path d="M9 7l6 0"></path>
              <path d="M9 11l6 0"></path>
              <path d="M9 15l4 0"></path>
            </svg>
            <span>Notes</span>
          </button>        ''', html, count=count)

    def render_template(self, bookmarks: [Bookmark], template: Template, url: str = '/test') -> str:
        rf = RequestFactory()
        request = rf.get(url)
        request.user = self.get_or_create_test_user()
        paginator = Paginator(bookmarks, 10)
        page = paginator.page(1)

        context = RequestContext(request, {'bookmarks': page, 'return_url': '/test'})
        return template.render(context)

    def render_default_template(self, bookmarks: [Bookmark], url: str = '/test') -> str:
        template = Template(
            '{% load bookmarks %}'
            '{% bookmark_list bookmarks return_url %}'
        )
        return self.render_template(bookmarks, template, url)

    def render_template_with_link_target(self, bookmarks: [Bookmark], link_target: str) -> str:
        template = Template(
            f'''
            {{% load bookmarks %}}
            {{% bookmark_list bookmarks return_url '{link_target}' %}}
            '''
        )
        return self.render_template(bookmarks, template)

    def setup_date_format_test(self, date_display_setting: str, web_archive_url: str = ''):
        bookmark = self.setup_bookmark()
        bookmark.date_added = timezone.now() - relativedelta(days=8)
        bookmark.web_archive_snapshot_url = web_archive_url
        bookmark.save()
        user = self.get_or_create_test_user()
        user.profile.bookmark_date_display = date_display_setting
        user.profile.save()
        return bookmark

    def test_should_respect_absolute_date_setting(self):
        bookmark = self.setup_date_format_test(UserProfile.BOOKMARK_DATE_DISPLAY_ABSOLUTE)
        html = self.render_default_template([bookmark])
        formatted_date = formats.date_format(bookmark.date_added, 'SHORT_DATE_FORMAT')

        self.assertDateLabel(html, formatted_date)

    def test_should_render_web_archive_link_with_absolute_date_setting(self):
        bookmark = self.setup_date_format_test(UserProfile.BOOKMARK_DATE_DISPLAY_ABSOLUTE,
                                               'https://web.archive.org/web/20210811214511/https://wanikani.com/')
        html = self.render_default_template([bookmark])
        formatted_date = formats.date_format(bookmark.date_added, 'SHORT_DATE_FORMAT')

        self.assertWebArchiveLink(html, formatted_date, bookmark.web_archive_snapshot_url)

    def test_should_respect_relative_date_setting(self):
        bookmark = self.setup_date_format_test(UserProfile.BOOKMARK_DATE_DISPLAY_RELATIVE)
        html = self.render_default_template([bookmark])

        self.assertDateLabel(html, '1 week ago')

    def test_should_render_web_archive_link_with_relative_date_setting(self):
        bookmark = self.setup_date_format_test(UserProfile.BOOKMARK_DATE_DISPLAY_RELATIVE,
                                               'https://web.archive.org/web/20210811214511/https://wanikani.com/')
        html = self.render_default_template([bookmark])

        self.assertWebArchiveLink(html, '1 week ago', bookmark.web_archive_snapshot_url)

    def test_bookmark_link_target_should_be_blank_by_default(self):
        bookmark = self.setup_bookmark()

        html = self.render_default_template([bookmark])

        self.assertBookmarksLink(html, bookmark, link_target='_blank')

    def test_bookmark_link_target_should_respect_link_target_parameter(self):
        bookmark = self.setup_bookmark()

        html = self.render_template_with_link_target([bookmark], '_self')

        self.assertBookmarksLink(html, bookmark, link_target='_self')

    def test_bookmark_link_target_should_respect_unread_flag(self):
        bookmark = self.setup_bookmark()
        html = self.render_template_with_link_target([bookmark], '_self')
        self.assertBookmarksLink(html, bookmark, link_target='_self', unread=False)

        bookmark = self.setup_bookmark(unread=True)
        html = self.render_template_with_link_target([bookmark], '_self')
        self.assertBookmarksLink(html, bookmark, link_target='_self', unread=True)

    def test_web_archive_link_target_should_be_blank_by_default(self):
        bookmark = self.setup_bookmark()
        bookmark.date_added = timezone.now() - relativedelta(days=8)
        bookmark.web_archive_snapshot_url = 'https://example.com'
        bookmark.save()

        html = self.render_default_template([bookmark])

        self.assertWebArchiveLink(html, '1 week ago', bookmark.web_archive_snapshot_url, link_target='_blank')

    def test_web_archive_link_target_respect_link_target_parameter(self):
        bookmark = self.setup_bookmark()
        bookmark.date_added = timezone.now() - relativedelta(days=8)
        bookmark.web_archive_snapshot_url = 'https://example.com'
        bookmark.save()

        html = self.render_template_with_link_target([bookmark], '_self')

        self.assertWebArchiveLink(html, '1 week ago', bookmark.web_archive_snapshot_url, link_target='_self')

    def test_show_bookmark_actions_for_owned_bookmarks(self):
        bookmark = self.setup_bookmark()
        html = self.render_default_template([bookmark])

        self.assertBookmarkActions(html, bookmark)
        self.assertNoShareInfo(html, bookmark)

    def test_show_share_info_for_non_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark = self.setup_bookmark(user=other_user)
        html = self.render_default_template([bookmark])

        self.assertNoBookmarkActions(html, bookmark)
        self.assertShareInfo(html, bookmark)

    def test_share_info_user_link_keeps_query_params(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        bookmark = self.setup_bookmark(user=other_user)
        html = self.render_default_template([bookmark], url='/test?q=foo')

        self.assertInHTML(f'''
            <span>Shared by 
                <a href="?q=foo&user={bookmark.owner.username}">{bookmark.owner.username}</a>
            </span>
        ''', html)

    def test_favicon_should_be_visible_when_favicons_enabled(self):
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = True
        profile.save()

        bookmark = self.setup_bookmark(favicon_file='https_example_com.png')
        html = self.render_default_template([bookmark])

        self.assertFaviconVisible(html, bookmark)

    def test_favicon_should_be_hidden_when_there_is_no_icon(self):
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = True
        profile.save()

        bookmark = self.setup_bookmark(favicon_file='')
        html = self.render_default_template([bookmark])

        self.assertFaviconHidden(html, bookmark)

    def test_favicon_should_be_hidden_when_favicons_disabled(self):
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = False
        profile.save()

        bookmark = self.setup_bookmark(favicon_file='https_example_com.png')
        html = self.render_default_template([bookmark])

        self.assertFaviconHidden(html, bookmark)

    def test_bookmark_url_should_be_hidden_by_default(self):
        profile = self.get_or_create_test_user().profile
        profile.save()

        bookmark = self.setup_bookmark()
        html = self.render_default_template([bookmark])

        self.assertBookmarkURLHidden(html, bookmark)

    def test_show_bookmark_url_when_enabled(self):
        profile = self.get_or_create_test_user().profile
        profile.display_url = True
        profile.save()

        bookmark = self.setup_bookmark()
        html = self.render_default_template([bookmark])

        self.assertBookmarkURLVisible(html, bookmark)

    def test_hide_bookmark_url_when_disabled(self):
        profile = self.get_or_create_test_user().profile
        profile.display_url = False
        profile.save()

        bookmark = self.setup_bookmark()
        html = self.render_default_template([bookmark])

        self.assertBookmarkURLHidden(html, bookmark)

    def test_without_notes(self):
        bookmark = self.setup_bookmark()
        html = self.render_default_template([bookmark])

        self.assertNotes(html, '', 0)
        self.assertNotesToggle(html, 0)

    def test_with_notes(self):
        bookmark = self.setup_bookmark(notes='Test note')
        html = self.render_default_template([bookmark])

        note_html = '<p>Test note</p>'
        self.assertNotes(html, note_html, 1)
        self.assertNotesToggle(html, 1)

    def test_note_renders_markdown(self):
        bookmark = self.setup_bookmark(notes='**Example:** `print("Hello world!")`')
        html = self.render_default_template([bookmark])

        note_html = '<p><strong>Example:</strong> <code>print("Hello world!")</code></p>'
        self.assertNotes(html, note_html, 1)
        self.assertNotesToggle(html, 1)

    def test_note_cleans_html(self):
        bookmark = self.setup_bookmark(notes='<script>alert("test")</script>')
        html = self.render_default_template([bookmark])

        note_html = '&lt;script&gt;alert("test")&lt;/script&gt;'
        self.assertNotes(html, note_html, 1)
