from typing import List

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark, Tag, UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkSharedViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertVisibleBookmarks(self, response, bookmarks: [Bookmark], link_target: str = '_blank'):
        html = response.content.decode()
        self.assertContains(response, 'data-is-bookmark-item', count=len(bookmarks))

        for bookmark in bookmarks:
            self.assertInHTML(
                f'<a href="{bookmark.url}" target="{link_target}" rel="noopener" class="">{bookmark.resolved_title}</a>',
                html
            )

    def assertInvisibleBookmarks(self, response, bookmarks: [Bookmark], link_target: str = '_blank'):
        html = response.content.decode()

        for bookmark in bookmarks:
            self.assertInHTML(
                f'<a href="{bookmark.url}" target="{link_target}" rel="noopener" class="">{bookmark.resolved_title}</a>',
                html,
                count=0
            )

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

    def test_should_list_shared_bookmarks_from_all_users(self):
        user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password123')
        user3 = User.objects.create_user('user3', 'user3@example.com', 'password123')

        visible_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user2),
            self.setup_bookmark(shared=True, user=user3),
        ]
        invisible_bookmarks = [
            self.setup_bookmark(shared=False),
        ]

        response = self.client.get(reverse('bookmarks:shared'))

        self.assertContains(response, '<ul class="bookmark-list">')  # Should render list
        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_shared_bookmarks_from_selected_user(self):
        user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password123')
        user3 = User.objects.create_user('user3', 'user3@example.com', 'password123')

        visible_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
        ]
        invisible_bookmarks = [
            self.setup_bookmark(shared=True, user=user2),
            self.setup_bookmark(shared=True, user=user3),
        ]

        url = reverse('bookmarks:shared') + '?user=user1'
        response = self.client.get(url)

        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_bookmarks_matching_query(self):
        visible_bookmarks = [
            self.setup_bookmark(shared=True, title='searchvalue'),
            self.setup_bookmark(shared=True, title='searchvalue'),
            self.setup_bookmark(shared=True, title='searchvalue')
        ]
        invisible_bookmarks = [
            self.setup_bookmark(shared=True),
            self.setup_bookmark(shared=True),
            self.setup_bookmark(shared=True)
        ]

        response = self.client.get(reverse('bookmarks:shared') + '?q=searchvalue')

        self.assertContains(response, '<ul class="bookmark-list">')  # Should render list
        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_tags_for_shared_bookmarks_from_all_users(self):
        user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password123')
        user3 = User.objects.create_user('user3', 'user3@example.com', 'password123')
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

        self.setup_bookmark(shared=True, user=user1, tags=[visible_tags[0]])
        self.setup_bookmark(shared=True, user=user2, tags=[visible_tags[1]])
        self.setup_bookmark(shared=True, user=user3, tags=[visible_tags[2]])

        self.setup_bookmark(shared=False, user=user1, tags=[invisible_tags[0]])
        self.setup_bookmark(shared=False, user=user2, tags=[invisible_tags[1]])
        self.setup_bookmark(shared=False, user=user3, tags=[invisible_tags[2]])

        response = self.client.get(reverse('bookmarks:shared'))

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_tags_for_shared_bookmarks_from_selected_user(self):
        user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password123')
        user3 = User.objects.create_user('user3', 'user3@example.com', 'password123')
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

        url = reverse('bookmarks:shared') + '?user=user1'
        response = self.client.get(url)

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_tags_for_bookmarks_matching_query(self):
        user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password123')
        user3 = User.objects.create_user('user3', 'user3@example.com', 'password123')
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

    def test_should_list_users_with_shared_bookmarks(self):
        users_with_shared_bookmarks = [
            User.objects.create_user('user1', 'user1@example.com', 'password123'),
            User.objects.create_user('user2', 'user2@example.com', 'password123'),
        ]
        self.setup_bookmark(shared=True, user=users_with_shared_bookmarks[0])
        self.setup_bookmark(shared=True, user=users_with_shared_bookmarks[1])

        users_without_shared_bookmarks = [
            User.objects.create_user('user3', 'user3@example.com', 'password123'),
            User.objects.create_user('user4', 'user4@example.com', 'password123'),
        ]
        self.setup_bookmark(shared=False, user=users_without_shared_bookmarks[0])
        self.setup_bookmark(shared=False, user=users_without_shared_bookmarks[1])

        response = self.client.get(reverse('bookmarks:shared'))
        self.assertVisibleUserOptions(response, users_with_shared_bookmarks)
        self.assertInvisibleUserOptions(response, users_without_shared_bookmarks)


def test_should_open_bookmarks_in_new_page_by_default(self):
    visible_bookmarks = [
        self.setup_bookmark(shared=True),
        self.setup_bookmark(shared=True),
        self.setup_bookmark(shared=True)
    ]

    response = self.client.get(reverse('bookmarks:shared'))

    self.assertVisibleBookmarks(response, visible_bookmarks, '_blank')


def test_should_open_bookmarks_in_same_page_if_specified_in_user_profile(self):
    user = self.get_or_create_test_user()
    user.profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_SELF
    user.profile.save()

    visible_bookmarks = [
        self.setup_bookmark(shared=True),
        self.setup_bookmark(shared=True),
        self.setup_bookmark(shared=True)
    ]

    response = self.client.get(reverse('bookmarks:shared'))

    self.assertVisibleBookmarks(response, visible_bookmarks, '_self')
