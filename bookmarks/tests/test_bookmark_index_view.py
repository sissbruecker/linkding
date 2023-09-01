import urllib.parse
from typing import List

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark, Tag, UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin, collapse_whitespace


class BookmarkIndexViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertVisibleBookmarks(self, response, bookmarks: List[Bookmark], link_target: str = '_blank'):
        html = response.content.decode()
        self.assertContains(response, '<li ld-bookmark-item>', count=len(bookmarks))

        for bookmark in bookmarks:
            self.assertInHTML(
                f'<a href="{bookmark.url}" target="{link_target}" rel="noopener">{bookmark.resolved_title}</a>',
                html
            )

    def assertInvisibleBookmarks(self, response, bookmarks: List[Bookmark], link_target: str = '_blank'):
        html = response.content.decode()

        for bookmark in bookmarks:
            self.assertInHTML(
                f'<a href="{bookmark.url}" target="{link_target}" rel="noopener">{bookmark.resolved_title}</a>',
                html,
                count=0
            )

    def assertVisibleTags(self, response, tags: List[Tag]):
        self.assertContains(response, 'data-is-tag-item', count=len(tags))

        for tag in tags:
            self.assertContains(response, tag.name)

    def assertInvisibleTags(self, response, tags: List[Tag]):
        for tag in tags:
            self.assertNotContains(response, tag.name)

    def assertSelectedTags(self, response, tags: List[Tag]):
        soup = self.make_soup(response.content.decode())
        selected_tags = soup.select('p.selected-tags')[0]
        self.assertIsNotNone(selected_tags)

        tag_list = selected_tags.select('a')
        self.assertEqual(len(tag_list), len(tags))

        for tag in tags:
            self.assertTrue(tag.name in selected_tags.text, msg=f'Selected tags do not contain: {tag.name}')

    def assertEditLink(self, response, url):
        html = response.content.decode()
        self.assertInHTML(f'''
            <a href="{url}">Edit</a>        
        ''', html)

    def assertBulkActionForm(self, response, url: str):
        html = collapse_whitespace(response.content.decode())
        needle = collapse_whitespace(f'''
            <form class="bookmark-actions"
                action="{url}"
                method="post" autocomplete="off">
        ''')
        self.assertIn(needle, html)

    def test_should_list_unarchived_and_user_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        visible_bookmarks = [
            self.setup_bookmark(),
            self.setup_bookmark(),
            self.setup_bookmark()
        ]
        invisible_bookmarks = [
            self.setup_bookmark(is_archived=True),
            self.setup_bookmark(user=other_user),
        ]

        response = self.client.get(reverse('bookmarks:index'))
        html = collapse_whitespace(response.content.decode())

        # Should render list
        self.assertIn('<ul class="bookmark-list" data-bookmarks-total="3">', html)
        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_bookmarks_matching_query(self):
        visible_bookmarks = [
            self.setup_bookmark(title='searchvalue'),
            self.setup_bookmark(title='searchvalue'),
            self.setup_bookmark(title='searchvalue')
        ]
        invisible_bookmarks = [
            self.setup_bookmark(),
            self.setup_bookmark(),
            self.setup_bookmark()
        ]

        response = self.client.get(reverse('bookmarks:index') + '?q=searchvalue')
        html = collapse_whitespace(response.content.decode())

        # Should render list
        self.assertIn('<ul class="bookmark-list" data-bookmarks-total="3">', html)
        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_tags_for_unarchived_and_user_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        visible_tags = [
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
        ]
        invisible_tags = [
            self.setup_tag(),  # unused tag
            self.setup_tag(),  # used in archived bookmark
            self.setup_tag(user=other_user),  # belongs to other user
        ]

        # Assign tags to some bookmarks with duplicates
        self.setup_bookmark(tags=[visible_tags[0]])
        self.setup_bookmark(tags=[visible_tags[0]])
        self.setup_bookmark(tags=[visible_tags[1]])
        self.setup_bookmark(tags=[visible_tags[1]])
        self.setup_bookmark(tags=[visible_tags[2]])
        self.setup_bookmark(tags=[visible_tags[2]])

        self.setup_bookmark(tags=[invisible_tags[1]], is_archived=True)
        self.setup_bookmark(tags=[invisible_tags[2]], user=other_user)

        response = self.client.get(reverse('bookmarks:index'))

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_tags_for_bookmarks_matching_query(self):
        visible_tags = [
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
        ]
        invisible_tags = [
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
        ]

        self.setup_bookmark(tags=[visible_tags[0]], title='searchvalue')
        self.setup_bookmark(tags=[visible_tags[1]], title='searchvalue')
        self.setup_bookmark(tags=[visible_tags[2]], title='searchvalue')
        self.setup_bookmark(tags=[invisible_tags[0]])
        self.setup_bookmark(tags=[invisible_tags[1]])
        self.setup_bookmark(tags=[invisible_tags[2]])

        response = self.client.get(reverse('bookmarks:index') + '?q=searchvalue')

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_display_selected_tags_from_query(self):
        tags = [
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
        ]
        self.setup_bookmark(tags=tags)

        response = self.client.get(reverse('bookmarks:index') + f'?q=%23{tags[0].name}+%23{tags[1].name.upper()}')

        self.assertSelectedTags(response, [tags[0], tags[1]])

    def test_should_not_display_search_terms_from_query_as_selected_tags_in_strict_mode(self):
        tags = [
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
        ]
        self.setup_bookmark(title=tags[0].name, tags=tags)

        response = self.client.get(reverse('bookmarks:index') + f'?q={tags[0].name}+%23{tags[1].name.upper()}')

        self.assertSelectedTags(response, [tags[1]])

    def test_should_display_search_terms_from_query_as_selected_tags_in_lax_mode(self):
        self.user.profile.tag_search = UserProfile.TAG_SEARCH_LAX
        self.user.profile.save()

        tags = [
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
        ]
        self.setup_bookmark(tags=tags)

        response = self.client.get(reverse('bookmarks:index') + f'?q={tags[0].name}+%23{tags[1].name.upper()}')

        self.assertSelectedTags(response, [tags[0], tags[1]])

    def test_should_open_bookmarks_in_new_page_by_default(self):
        visible_bookmarks = [
            self.setup_bookmark(),
            self.setup_bookmark(),
            self.setup_bookmark()
        ]

        response = self.client.get(reverse('bookmarks:index'))

        self.assertVisibleBookmarks(response, visible_bookmarks, '_blank')

    def test_should_open_bookmarks_in_same_page_if_specified_in_user_profile(self):
        user = self.get_or_create_test_user()
        user.profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_SELF
        user.profile.save()

        visible_bookmarks = [
            self.setup_bookmark(),
            self.setup_bookmark(),
            self.setup_bookmark()
        ]

        response = self.client.get(reverse('bookmarks:index'))

        self.assertVisibleBookmarks(response, visible_bookmarks, '_self')

    def test_edit_link_return_url_respects_search_options(self):
        bookmark = self.setup_bookmark(title='foo')
        edit_url = reverse('bookmarks:edit', args=[bookmark.id])
        base_url = reverse('bookmarks:index')

        # without query params
        return_url = urllib.parse.quote(base_url)
        url = f'{edit_url}?return_url={return_url}'

        response = self.client.get(base_url)
        self.assertEditLink(response, url)

        # with query
        url_params = '?q=foo'
        return_url = urllib.parse.quote(base_url + url_params)
        url = f'{edit_url}?return_url={return_url}'

        response = self.client.get(base_url + url_params)
        self.assertEditLink(response, url)

        # with query and sort and page
        url_params = '?q=foo&sort=title_asc&page=2'
        return_url = urllib.parse.quote(base_url + url_params)
        url = f'{edit_url}?return_url={return_url}'

        response = self.client.get(base_url + url_params)
        self.assertEditLink(response, url)

    def test_bulk_edit_respects_search_options(self):
        action_url = reverse('bookmarks:index.action')
        base_url = reverse('bookmarks:index')

        # without params
        return_url = urllib.parse.quote_plus(base_url)
        url = f'{action_url}?return_url={return_url}'

        response = self.client.get(base_url)
        self.assertBulkActionForm(response, url)

        # with query
        url_params = '?q=foo'
        return_url = urllib.parse.quote_plus(base_url + url_params)
        url = f'{action_url}?q=foo&return_url={return_url}'

        response = self.client.get(base_url + url_params)
        self.assertBulkActionForm(response, url)

        # with query and sort
        url_params = '?q=foo&sort=title_asc'
        return_url = urllib.parse.quote_plus(base_url + url_params)
        url = f'{action_url}?q=foo&sort=title_asc&return_url={return_url}'

        response = self.client.get(base_url + url_params)
        self.assertBulkActionForm(response, url)

    def test_allowed_bulk_actions(self):
        url = reverse('bookmarks:index')
        response = self.client.get(url)
        html = response.content.decode()

        self.assertInHTML(f'''
          <select name="bulk_action" class="form-select select-sm">
            <option value="bulk_archive">Archive</option>
            <option value="bulk_delete">Delete</option>
            <option value="bulk_tag">Add tags</option>
            <option value="bulk_untag">Remove tags</option>
            <option value="bulk_read">Mark as read</option>
            <option value="bulk_unread">Mark as unread</option>
          </select>
        ''', html)

    def test_allowed_bulk_actions_with_sharing_enabled(self):
        user_profile = self.user.profile
        user_profile.enable_sharing = True
        user_profile.save()

        url = reverse('bookmarks:index')
        response = self.client.get(url)
        html = response.content.decode()

        self.assertInHTML(f'''
          <select name="bulk_action" class="form-select select-sm">
            <option value="bulk_archive">Archive</option>
            <option value="bulk_delete">Delete</option>
            <option value="bulk_tag">Add tags</option>
            <option value="bulk_untag">Remove tags</option>
            <option value="bulk_read">Mark as read</option>
            <option value="bulk_unread">Mark as unread</option>
            <option value="bulk_share">Share</option>
            <option value="bulk_unshare">Unshare</option>
          </select>
        ''', html)
