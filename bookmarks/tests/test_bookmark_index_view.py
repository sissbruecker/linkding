from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark, Tag
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkIndexViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertVisibleBookmarks(self, response, bookmarks: [Bookmark]):
        html = response.content.decode()
        self.assertContains(response, 'data-is-bookmark-item', count=len(bookmarks))

        for bookmark in bookmarks:
            self.assertInHTML(
                '<a href="{0}" target="_blank" rel="noopener">{1}</a>'.format(bookmark.url, bookmark.resolved_title),
                html
            )

    def assertInvisibleBookmarks(self, response, bookmarks: [Bookmark]):
        html = response.content.decode()

        for bookmark in bookmarks:
            self.assertInHTML(
                '<a href="{0}" target="_blank" rel="noopener">{1}</a>'.format(bookmark.url, bookmark.resolved_title),
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

        self.assertContains(response, '<ul class="bookmark-list">')  # Should render list
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

        self.assertContains(response, '<ul class="bookmark-list">')  # Should render list
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

        self.setup_bookmark(tags=[visible_tags[0]], title='searchvalue'),
        self.setup_bookmark(tags=[visible_tags[1]], title='searchvalue')
        self.setup_bookmark(tags=[visible_tags[2]], title='searchvalue')
        self.setup_bookmark(tags=[invisible_tags[0]])
        self.setup_bookmark(tags=[invisible_tags[1]])
        self.setup_bookmark(tags=[invisible_tags[2]])

        response = self.client.get(reverse('bookmarks:index') + '?q=searchvalue')

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)
