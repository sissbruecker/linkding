from typing import List

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark, Tag, UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, collapse_whitespace, HtmlTestMixin


class BookmarkSharedViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):

    def authenticate(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertBookmarkCount(self, html: str, bookmark: Bookmark, count: int, link_target: str = '_blank'):
        self.assertInHTML(
            f'<a href="{bookmark.url}" target="{link_target}" rel="noopener">{bookmark.resolved_title}</a>',
            html, count=count
        )

    def assertVisibleBookmarks(self, response, bookmarks: List[Bookmark], link_target: str = '_blank'):
        html = response.content.decode()
        self.assertContains(response, '<li ld-bookmark-item class="shared">', count=len(bookmarks))

        for bookmark in bookmarks:
            self.assertBookmarkCount(html, bookmark, 1, link_target)

    def assertInvisibleBookmarks(self, response, bookmarks: List[Bookmark], link_target: str = '_blank'):
        html = response.content.decode()

        for bookmark in bookmarks:
            self.assertBookmarkCount(html, bookmark, 0, link_target)

    def assertVisibleTags(self, response, tags: [Tag]):
        self.assertContains(response, 'data-is-tag-item', count=len(tags))

        for tag in tags:
            self.assertContains(response, tag.name)

    def assertInvisibleTags(self, response, tags: [Tag]):
        for tag in tags:
            self.assertNotContains(response, tag.name)

    def assertVisibleUserOptions(self, response, users: List[User]):
        html = response.content.decode()
        self.assertContains(response, 'data-is-user-option', count=len(users))

        for user in users:
            self.assertInHTML(f'''
              <option value="{user.username}" data-is-user-option>
                {user.username}
              </option>        
            ''', html)

    def assertInvisibleUserOptions(self, response, users: List[User]):
        html = response.content.decode()

        for user in users:
            self.assertInHTML(f'''
              <option value="{user.username}" data-is-user-option>
                {user.username}
              </option>        
            ''', html, count=0)

    def test_should_list_shared_bookmarks_from_all_users_that_have_sharing_enabled(self):
        self.authenticate()
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        user4 = self.setup_user(enable_sharing=False)

        visible_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user2),
            self.setup_bookmark(shared=True, user=user3),
        ]
        invisible_bookmarks = [
            self.setup_bookmark(shared=False, user=user1),
            self.setup_bookmark(shared=False, user=user2),
            self.setup_bookmark(shared=False, user=user3),
            self.setup_bookmark(shared=True, user=user4),
        ]

        response = self.client.get(reverse('bookmarks:shared'))
        html = collapse_whitespace(response.content.decode())

        # Should render list
        self.assertIn('<ul class="bookmark-list" data-bookmarks-total="3">', html)
        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_shared_bookmarks_from_selected_user(self):
        self.authenticate()
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)

        visible_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
        ]
        invisible_bookmarks = [
            self.setup_bookmark(shared=True, user=user2),
            self.setup_bookmark(shared=True, user=user3),
        ]

        url = reverse('bookmarks:shared') + '?user=' + user1.username
        response = self.client.get(url)

        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_bookmarks_matching_query(self):
        self.authenticate()
        user = self.setup_user(enable_sharing=True)
        visible_bookmarks = [
            self.setup_bookmark(shared=True, title='searchvalue', user=user),
            self.setup_bookmark(shared=True, title='searchvalue', user=user),
            self.setup_bookmark(shared=True, title='searchvalue', user=user)
        ]
        invisible_bookmarks = [
            self.setup_bookmark(shared=True, user=user),
            self.setup_bookmark(shared=True, user=user),
            self.setup_bookmark(shared=True, user=user)
        ]

        response = self.client.get(reverse('bookmarks:shared') + '?q=searchvalue')
        html = collapse_whitespace(response.content.decode())

        # Should render list
        self.assertIn('<ul class="bookmark-list" data-bookmarks-total="3">', html)
        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_only_publicly_shared_bookmarks_without_login(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True)

        visible_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user1),
        ]
        invisible_bookmarks = [
            self.setup_bookmark(shared=True, user=user2),
            self.setup_bookmark(shared=True, user=user2),
            self.setup_bookmark(shared=True, user=user2),
        ]

        response = self.client.get(reverse('bookmarks:shared'))
        html = collapse_whitespace(response.content.decode())

        # Should render list
        self.assertIn('<ul class="bookmark-list" data-bookmarks-total="3">', html)
        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_tags_for_shared_bookmarks_from_all_users_that_have_sharing_enabled(self):
        self.authenticate()
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        user4 = self.setup_user(enable_sharing=False)
        visible_tags = [
            self.setup_tag(user=user1),
            self.setup_tag(user=user2),
            self.setup_tag(user=user3),
        ]
        invisible_tags = [
            self.setup_tag(user=user1),
            self.setup_tag(user=user2),
            self.setup_tag(user=user3),
            self.setup_tag(user=user4),
        ]

        self.setup_bookmark(shared=True, user=user1, tags=[visible_tags[0]])
        self.setup_bookmark(shared=True, user=user2, tags=[visible_tags[1]])
        self.setup_bookmark(shared=True, user=user3, tags=[visible_tags[2]])

        self.setup_bookmark(shared=False, user=user1, tags=[invisible_tags[0]])
        self.setup_bookmark(shared=False, user=user2, tags=[invisible_tags[1]])
        self.setup_bookmark(shared=False, user=user3, tags=[invisible_tags[2]])
        self.setup_bookmark(shared=True, user=user4, tags=[invisible_tags[3]])

        response = self.client.get(reverse('bookmarks:shared'))

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_tags_for_shared_bookmarks_from_selected_user(self):
        self.authenticate()
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        visible_tags = [
            self.setup_tag(user=user1),
        ]
        invisible_tags = [
            self.setup_tag(user=user2),
            self.setup_tag(user=user3),
        ]

        self.setup_bookmark(shared=True, user=user1, tags=[visible_tags[0]])
        self.setup_bookmark(shared=True, user=user2, tags=[invisible_tags[0]])
        self.setup_bookmark(shared=True, user=user3, tags=[invisible_tags[1]])

        url = reverse('bookmarks:shared') + '?user=' + user1.username
        response = self.client.get(url)

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_tags_for_bookmarks_matching_query(self):
        self.authenticate()
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        visible_tags = [
            self.setup_tag(user=user1),
            self.setup_tag(user=user2),
            self.setup_tag(user=user3),
        ]
        invisible_tags = [
            self.setup_tag(user=user1),
            self.setup_tag(user=user2),
            self.setup_tag(user=user3),
        ]

        self.setup_bookmark(shared=True, user=user1, title='searchvalue', tags=[visible_tags[0]])
        self.setup_bookmark(shared=True, user=user2, title='searchvalue', tags=[visible_tags[1]])
        self.setup_bookmark(shared=True, user=user3, title='searchvalue', tags=[visible_tags[2]])

        self.setup_bookmark(shared=True, user=user1, tags=[invisible_tags[0]])
        self.setup_bookmark(shared=True, user=user2, tags=[invisible_tags[1]])
        self.setup_bookmark(shared=True, user=user3, tags=[invisible_tags[2]])

        response = self.client.get(reverse('bookmarks:shared') + '?q=searchvalue')

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_only_tags_for_publicly_shared_bookmarks_without_login(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True)

        visible_tags = [
            self.setup_tag(user=user1),
            self.setup_tag(user=user1),
        ]
        invisible_tags = [
            self.setup_tag(user=user2),
            self.setup_tag(user=user2),
        ]

        self.setup_bookmark(shared=True, user=user1, tags=[visible_tags[0]])
        self.setup_bookmark(shared=True, user=user1, tags=[visible_tags[1]])

        self.setup_bookmark(shared=True, user=user2, tags=[invisible_tags[0]])
        self.setup_bookmark(shared=True, user=user2, tags=[invisible_tags[1]])

        response = self.client.get(reverse('bookmarks:shared'))

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_users_with_shared_bookmarks_if_sharing_is_enabled(self):
        self.authenticate()
        expected_visible_users = [
            self.setup_user(enable_sharing=True),
            self.setup_user(enable_sharing=True),
        ]
        self.setup_bookmark(shared=True, user=expected_visible_users[0])
        self.setup_bookmark(shared=True, user=expected_visible_users[1])

        expected_invisible_users = [
            self.setup_user(enable_sharing=True),
            self.setup_user(enable_sharing=False),
        ]
        self.setup_bookmark(shared=False, user=expected_invisible_users[0])
        self.setup_bookmark(shared=True, user=expected_invisible_users[1])

        response = self.client.get(reverse('bookmarks:shared'))
        self.assertVisibleUserOptions(response, expected_visible_users)
        self.assertInvisibleUserOptions(response, expected_invisible_users)

    def test_should_list_only_users_with_publicly_shared_bookmarks_without_login(self):
        expected_visible_users = [
            self.setup_user(enable_sharing=True, enable_public_sharing=True),
            self.setup_user(enable_sharing=True, enable_public_sharing=True),
        ]
        self.setup_bookmark(shared=True, user=expected_visible_users[0])
        self.setup_bookmark(shared=True, user=expected_visible_users[1])

        expected_invisible_users = [
            self.setup_user(enable_sharing=True),
            self.setup_user(enable_sharing=True),
        ]
        self.setup_bookmark(shared=True, user=expected_invisible_users[0])
        self.setup_bookmark(shared=True, user=expected_invisible_users[1])

        response = self.client.get(reverse('bookmarks:shared'))
        self.assertVisibleUserOptions(response, expected_visible_users)
        self.assertInvisibleUserOptions(response, expected_invisible_users)

    def test_should_open_bookmarks_in_new_page_by_default(self):
        self.authenticate()
        user = self.get_or_create_test_user()
        user.profile.enable_sharing = True
        user.profile.save()
        visible_bookmarks = [
            self.setup_bookmark(shared=True),
            self.setup_bookmark(shared=True),
            self.setup_bookmark(shared=True)
        ]

        response = self.client.get(reverse('bookmarks:shared'))

        self.assertVisibleBookmarks(response, visible_bookmarks, '_blank')

    def test_should_open_bookmarks_in_same_page_if_specified_in_user_profile(self):
        self.authenticate()
        user = self.get_or_create_test_user()
        user.profile.enable_sharing = True
        user.profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_SELF
        user.profile.save()

        visible_bookmarks = [
            self.setup_bookmark(shared=True),
            self.setup_bookmark(shared=True),
            self.setup_bookmark(shared=True)
        ]

        response = self.client.get(reverse('bookmarks:shared'))

        self.assertVisibleBookmarks(response, visible_bookmarks, '_self')

    def test_url_encode_bookmark_actions_url(self):
        url = reverse('bookmarks:shared') + '?q=%23foo'
        response = self.client.get(url)
        html = response.content.decode()
        soup = self.make_soup(html)
        actions_form = soup.select('form.bookmark-actions')[0]

        self.assertEqual(actions_form.attrs['action'],
                         '/bookmarks/shared/action?q=%23foo&return_url=%2Fbookmarks%2Fshared%3Fq%3D%2523foo')
