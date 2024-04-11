import urllib.parse
from typing import List

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark, BookmarkSearch, Tag, UserProfile
from bookmarks.tests.helpers import (
    BookmarkFactoryMixin,
    HtmlTestMixin,
    collapse_whitespace,
)


class BookmarkIndexViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def assertVisibleBookmarks(
        self, response, bookmarks: List[Bookmark], link_target: str = "_blank"
    ):
        soup = self.make_soup(response.content.decode())
        bookmark_list = soup.select_one(
            f'ul.bookmark-list[data-bookmarks-total="{len(bookmarks)}"]'
        )
        self.assertIsNotNone(bookmark_list)

        bookmark_items = bookmark_list.select("li[ld-bookmark-item]")
        self.assertEqual(len(bookmark_items), len(bookmarks))

        for bookmark in bookmarks:
            bookmark_item = bookmark_list.select_one(
                f'li[ld-bookmark-item] a[href="{bookmark.url}"][target="{link_target}"]'
            )
            self.assertIsNotNone(bookmark_item)

    def assertInvisibleBookmarks(
        self, response, bookmarks: List[Bookmark], link_target: str = "_blank"
    ):
        soup = self.make_soup(response.content.decode())

        for bookmark in bookmarks:
            bookmark_item = soup.select_one(
                f'li[ld-bookmark-item] a[href="{bookmark.url}"][target="{link_target}"]'
            )
            self.assertIsNone(bookmark_item)

    def assertVisibleTags(self, response, tags: List[Tag]):
        soup = self.make_soup(response.content.decode())
        tag_cloud = soup.select_one("div.tag-cloud")
        self.assertIsNotNone(tag_cloud)

        tag_items = tag_cloud.select("a[data-is-tag-item]")
        self.assertEqual(len(tag_items), len(tags))

        tag_item_names = [tag_item.text.strip() for tag_item in tag_items]

        for tag in tags:
            self.assertTrue(tag.name in tag_item_names)

    def assertInvisibleTags(self, response, tags: List[Tag]):
        soup = self.make_soup(response.content.decode())
        tag_items = soup.select("a[data-is-tag-item]")

        tag_item_names = [tag_item.text.strip() for tag_item in tag_items]

        for tag in tags:
            self.assertFalse(tag.name in tag_item_names)

    def assertSelectedTags(self, response, tags: List[Tag]):
        soup = self.make_soup(response.content.decode())
        selected_tags = soup.select_one("p.selected-tags")
        self.assertIsNotNone(selected_tags)

        tag_list = selected_tags.select("a")
        self.assertEqual(len(tag_list), len(tags))

        for tag in tags:
            self.assertTrue(
                tag.name in selected_tags.text,
                msg=f"Selected tags do not contain: {tag.name}",
            )

    def assertEditLink(self, response, url):
        html = response.content.decode()
        self.assertInHTML(
            f"""
            <a href="{url}">Edit</a>        
        """,
            html,
        )

    def assertBulkActionForm(self, response, url: str):
        soup = self.make_soup(response.content.decode())
        form = soup.select_one("form.bookmark-actions")
        self.assertIsNotNone(form)
        self.assertEqual(form.attrs["action"], url)

    def test_should_list_unarchived_and_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        visible_bookmarks = self.setup_numbered_bookmarks(3)
        invisible_bookmarks = [
            self.setup_bookmark(is_archived=True),
            self.setup_bookmark(user=other_user),
        ]

        response = self.client.get(reverse("bookmarks:index"))

        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_bookmarks_matching_query(self):
        visible_bookmarks = self.setup_numbered_bookmarks(3, prefix="foo")
        invisible_bookmarks = self.setup_numbered_bookmarks(3, prefix="bar")

        response = self.client.get(reverse("bookmarks:index") + "?q=foo")

        self.assertVisibleBookmarks(response, visible_bookmarks)
        self.assertInvisibleBookmarks(response, invisible_bookmarks)

    def test_should_list_tags_for_unarchived_and_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        visible_bookmarks = self.setup_numbered_bookmarks(3, with_tags=True)
        archived_bookmarks = self.setup_numbered_bookmarks(
            3, with_tags=True, archived=True, tag_prefix="archived"
        )
        other_user_bookmarks = self.setup_numbered_bookmarks(
            3, with_tags=True, user=other_user, tag_prefix="otheruser"
        )

        visible_tags = self.get_tags_from_bookmarks(visible_bookmarks)
        invisible_tags = self.get_tags_from_bookmarks(
            archived_bookmarks + other_user_bookmarks
        )

        response = self.client.get(reverse("bookmarks:index"))

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_tags_for_bookmarks_matching_query(self):
        visible_bookmarks = self.setup_numbered_bookmarks(
            3, with_tags=True, prefix="foo", tag_prefix="foo"
        )
        invisible_bookmarks = self.setup_numbered_bookmarks(
            3, with_tags=True, prefix="bar", tag_prefix="bar"
        )

        visible_tags = self.get_tags_from_bookmarks(visible_bookmarks)
        invisible_tags = self.get_tags_from_bookmarks(invisible_bookmarks)

        response = self.client.get(reverse("bookmarks:index") + "?q=foo")

        self.assertVisibleTags(response, visible_tags)
        self.assertInvisibleTags(response, invisible_tags)

    def test_should_list_bookmarks_and_tags_for_search_preferences(self):
        user_profile = self.user.profile
        user_profile.search_preferences = {
            "unread": BookmarkSearch.FILTER_UNREAD_YES,
        }
        user_profile.save()

        unread_bookmarks = self.setup_numbered_bookmarks(
            3, unread=True, with_tags=True, prefix="unread", tag_prefix="unread"
        )
        read_bookmarks = self.setup_numbered_bookmarks(
            3, unread=False, with_tags=True, prefix="read", tag_prefix="read"
        )

        unread_tags = self.get_tags_from_bookmarks(unread_bookmarks)
        read_tags = self.get_tags_from_bookmarks(read_bookmarks)

        response = self.client.get(reverse("bookmarks:index"))
        self.assertVisibleBookmarks(response, unread_bookmarks)
        self.assertInvisibleBookmarks(response, read_bookmarks)
        self.assertVisibleTags(response, unread_tags)
        self.assertInvisibleTags(response, read_tags)

    def test_should_display_selected_tags_from_query(self):
        tags = [
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
        ]
        self.setup_bookmark(tags=tags)

        response = self.client.get(
            reverse("bookmarks:index")
            + f"?q=%23{tags[0].name}+%23{tags[1].name.upper()}"
        )

        self.assertSelectedTags(response, [tags[0], tags[1]])

    def test_should_not_display_search_terms_from_query_as_selected_tags_in_strict_mode(
        self,
    ):
        tags = [
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
            self.setup_tag(),
        ]
        self.setup_bookmark(title=tags[0].name, tags=tags)

        response = self.client.get(
            reverse("bookmarks:index") + f"?q={tags[0].name}+%23{tags[1].name.upper()}"
        )

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

        response = self.client.get(
            reverse("bookmarks:index") + f"?q={tags[0].name}+%23{tags[1].name.upper()}"
        )

        self.assertSelectedTags(response, [tags[0], tags[1]])

    def test_should_open_bookmarks_in_new_page_by_default(self):
        visible_bookmarks = self.setup_numbered_bookmarks(3)

        response = self.client.get(reverse("bookmarks:index"))

        self.assertVisibleBookmarks(response, visible_bookmarks, "_blank")

    def test_should_open_bookmarks_in_same_page_if_specified_in_user_profile(self):
        user = self.get_or_create_test_user()
        user.profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_SELF
        user.profile.save()

        visible_bookmarks = self.setup_numbered_bookmarks(3)

        response = self.client.get(reverse("bookmarks:index"))

        self.assertVisibleBookmarks(response, visible_bookmarks, "_self")

    def test_edit_link_return_url_respects_search_options(self):
        bookmark = self.setup_bookmark(title="foo")
        edit_url = reverse("bookmarks:edit", args=[bookmark.id])
        base_url = reverse("bookmarks:index")

        # without query params
        return_url = urllib.parse.quote(base_url)
        url = f"{edit_url}?return_url={return_url}"

        response = self.client.get(base_url)
        self.assertEditLink(response, url)

        # with query
        url_params = "?q=foo"
        return_url = urllib.parse.quote(base_url + url_params)
        url = f"{edit_url}?return_url={return_url}"

        response = self.client.get(base_url + url_params)
        self.assertEditLink(response, url)

        # with query and sort and page
        url_params = "?q=foo&sort=title_asc&page=2"
        return_url = urllib.parse.quote(base_url + url_params)
        url = f"{edit_url}?return_url={return_url}"

        response = self.client.get(base_url + url_params)
        self.assertEditLink(response, url)

    def test_bulk_edit_respects_search_options(self):
        action_url = reverse("bookmarks:index.action")
        base_url = reverse("bookmarks:index")

        # without params
        return_url = urllib.parse.quote_plus(base_url)
        url = f"{action_url}?return_url={return_url}"

        response = self.client.get(base_url)
        self.assertBulkActionForm(response, url)

        # with query
        url_params = "?q=foo"
        return_url = urllib.parse.quote_plus(base_url + url_params)
        url = f"{action_url}?q=foo&return_url={return_url}"

        response = self.client.get(base_url + url_params)
        self.assertBulkActionForm(response, url)

        # with query and sort
        url_params = "?q=foo&sort=title_asc"
        return_url = urllib.parse.quote_plus(base_url + url_params)
        url = f"{action_url}?q=foo&sort=title_asc&return_url={return_url}"

        response = self.client.get(base_url + url_params)
        self.assertBulkActionForm(response, url)

    def test_allowed_bulk_actions(self):
        url = reverse("bookmarks:index")
        response = self.client.get(url)
        html = response.content.decode()

        self.assertInHTML(
            f"""
          <select name="bulk_action" class="form-select select-sm">
            <option value="bulk_archive">Archive</option>
            <option value="bulk_delete">Delete</option>
            <option value="bulk_tag">Add tags</option>
            <option value="bulk_untag">Remove tags</option>
            <option value="bulk_read">Mark as read</option>
            <option value="bulk_unread">Mark as unread</option>
          </select>
        """,
            html,
        )

    def test_allowed_bulk_actions_with_sharing_enabled(self):
        user_profile = self.user.profile
        user_profile.enable_sharing = True
        user_profile.save()

        url = reverse("bookmarks:index")
        response = self.client.get(url)
        html = response.content.decode()

        self.assertInHTML(
            f"""
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
        """,
            html,
        )

    def test_apply_search_preferences(self):
        # no params
        response = self.client.post(reverse("bookmarks:index"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("bookmarks:index"))

        # some params
        response = self.client.post(
            reverse("bookmarks:index"),
            {
                "q": "foo",
                "sort": BookmarkSearch.SORT_TITLE_ASC,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("bookmarks:index") + "?q=foo&sort=title_asc"
        )

        # params with default value are removed
        response = self.client.post(
            reverse("bookmarks:index"),
            {
                "q": "foo",
                "user": "",
                "sort": BookmarkSearch.SORT_ADDED_DESC,
                "shared": BookmarkSearch.FILTER_SHARED_OFF,
                "unread": BookmarkSearch.FILTER_UNREAD_YES,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("bookmarks:index") + "?q=foo&unread=yes")

        # page is removed
        response = self.client.post(
            reverse("bookmarks:index"),
            {
                "q": "foo",
                "page": "2",
                "sort": BookmarkSearch.SORT_TITLE_ASC,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("bookmarks:index") + "?q=foo&sort=title_asc"
        )

    def test_save_search_preferences(self):
        user_profile = self.user.profile

        # no params
        self.client.post(
            reverse("bookmarks:index"),
            {
                "save": "",
            },
        )
        user_profile.refresh_from_db()
        self.assertEqual(
            user_profile.search_preferences,
            {
                "sort": BookmarkSearch.SORT_ADDED_DESC,
                "shared": BookmarkSearch.FILTER_SHARED_OFF,
                "unread": BookmarkSearch.FILTER_UNREAD_OFF,
            },
        )

        # with param
        self.client.post(
            reverse("bookmarks:index"),
            {
                "save": "",
                "sort": BookmarkSearch.SORT_TITLE_ASC,
            },
        )
        user_profile.refresh_from_db()
        self.assertEqual(
            user_profile.search_preferences,
            {
                "sort": BookmarkSearch.SORT_TITLE_ASC,
                "shared": BookmarkSearch.FILTER_SHARED_OFF,
                "unread": BookmarkSearch.FILTER_UNREAD_OFF,
            },
        )

        # add a param
        self.client.post(
            reverse("bookmarks:index"),
            {
                "save": "",
                "sort": BookmarkSearch.SORT_TITLE_ASC,
                "unread": BookmarkSearch.FILTER_UNREAD_YES,
            },
        )
        user_profile.refresh_from_db()
        self.assertEqual(
            user_profile.search_preferences,
            {
                "sort": BookmarkSearch.SORT_TITLE_ASC,
                "shared": BookmarkSearch.FILTER_SHARED_OFF,
                "unread": BookmarkSearch.FILTER_UNREAD_YES,
            },
        )

        # remove a param
        self.client.post(
            reverse("bookmarks:index"),
            {
                "save": "",
                "unread": BookmarkSearch.FILTER_UNREAD_YES,
            },
        )
        user_profile.refresh_from_db()
        self.assertEqual(
            user_profile.search_preferences,
            {
                "sort": BookmarkSearch.SORT_ADDED_DESC,
                "shared": BookmarkSearch.FILTER_SHARED_OFF,
                "unread": BookmarkSearch.FILTER_UNREAD_YES,
            },
        )

        # ignores non-preferences
        self.client.post(
            reverse("bookmarks:index"),
            {
                "save": "",
                "q": "foo",
                "user": "john",
                "page": "3",
                "sort": BookmarkSearch.SORT_TITLE_ASC,
            },
        )
        user_profile.refresh_from_db()
        self.assertEqual(
            user_profile.search_preferences,
            {
                "sort": BookmarkSearch.SORT_TITLE_ASC,
                "shared": BookmarkSearch.FILTER_SHARED_OFF,
                "unread": BookmarkSearch.FILTER_UNREAD_OFF,
            },
        )

    def test_url_encode_bookmark_actions_url(self):
        url = reverse("bookmarks:index") + "?q=%23foo"
        response = self.client.get(url)
        html = response.content.decode()
        soup = self.make_soup(html)
        actions_form = soup.select("form.bookmark-actions")[0]

        self.assertEqual(
            actions_form.attrs["action"],
            "/bookmarks/action?q=%23foo&return_url=%2Fbookmarks%3Fq%3D%2523foo",
        )

    def test_encode_search_params(self):
        bookmark = self.setup_bookmark(description="alert('xss')")

        url = reverse("bookmarks:index") + "?q=alert(%27xss%27)"
        response = self.client.get(url)
        self.assertNotContains(response, "alert('xss')")
        self.assertContains(response, bookmark.url)

        url = reverse("bookmarks:index") + "?sort=alert(%27xss%27)"
        response = self.client.get(url)
        self.assertNotContains(response, "alert('xss')")

        url = reverse("bookmarks:index") + "?unread=alert(%27xss%27)"
        response = self.client.get(url)
        self.assertNotContains(response, "alert('xss')")

        url = reverse("bookmarks:index") + "?shared=alert(%27xss%27)"
        response = self.client.get(url)
        self.assertNotContains(response, "alert('xss')")

        url = reverse("bookmarks:index") + "?user=alert(%27xss%27)"
        response = self.client.get(url)
        self.assertNotContains(response, "alert('xss')")

        url = reverse("bookmarks:index") + "?page=alert(%27xss%27)"
        response = self.client.get(url)
        self.assertNotContains(response, "alert('xss')")
