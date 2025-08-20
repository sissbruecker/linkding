from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class BundlePreviewViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_preview_empty_bundle(self):
        bookmark1 = self.setup_bookmark(title="Test Bookmark 1")
        bookmark2 = self.setup_bookmark(title="Test Bookmark 2")

        response = self.client.get(reverse("linkding:bundles.preview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Found 2 bookmarks matching this bundle")
        self.assertContains(response, bookmark1.title)
        self.assertContains(response, bookmark2.title)
        self.assertNotContains(response, "No bookmarks match the current bundle")

    def test_preview_with_search_terms(self):
        bookmark1 = self.setup_bookmark(title="Python Programming")
        bookmark2 = self.setup_bookmark(title="JavaScript Tutorial")
        bookmark3 = self.setup_bookmark(title="Django Framework")

        response = self.client.get(
            reverse("linkding:bundles.preview"), {"search": "python"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Found 1 bookmarks matching this bundle")
        self.assertContains(response, bookmark1.title)
        self.assertNotContains(response, bookmark2.title)
        self.assertNotContains(response, bookmark3.title)

    def test_preview_no_matching_bookmarks(self):
        bookmark = self.setup_bookmark(title="Python Guide")

        response = self.client.get(
            reverse("linkding:bundles.preview"), {"search": "nonexistent"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No bookmarks match the current bundle")
        self.assertNotContains(response, bookmark.title)

    def test_preview_renders_bookmark(self):
        tag = self.setup_tag(name="test-tag")
        bookmark = self.setup_bookmark(
            title="Test Bookmark",
            description="Test description",
            url="https://example.com/test",
            tags=[tag],
        )

        response = self.client.get(reverse("linkding:bundles.preview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, bookmark.title)
        self.assertContains(response, bookmark.description)
        self.assertContains(response, bookmark.url)
        self.assertContains(response, "#test-tag")

    def test_preview_renders_bookmark_in_preview_mode(self):
        tag = self.setup_tag(name="test-tag")
        self.setup_bookmark(
            title="Test Bookmark",
            description="Test description",
            url="https://example.com/test",
            tags=[tag],
        )

        response = self.client.get(reverse("linkding:bundles.preview"))
        soup = self.make_soup(response.content.decode())

        list_item = soup.select_one("li[ld-bookmark-item]")
        actions = list_item.select(".actions > *")
        self.assertEqual(len(actions), 1)

    def test_preview_ignores_archived_bookmarks(self):
        active_bookmark = self.setup_bookmark(title="Active Bookmark")
        archived_bookmark = self.setup_bookmark(
            title="Archived Bookmark", is_archived=True
        )

        response = self.client.get(reverse("linkding:bundles.preview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Found 1 bookmarks matching this bundle")
        self.assertContains(response, active_bookmark.title)
        self.assertNotContains(response, archived_bookmark.title)

    def test_preview_requires_authentication(self):
        self.client.logout()

        response = self.client.get(reverse("linkding:bundles.preview"), follow=True)

        self.assertRedirects(
            response, f"/login/?next={reverse('linkding:bundles.preview')}"
        )

    def test_preview_only_shows_user_bookmarks(self):
        other_user = self.setup_user()
        own_bookmark = self.setup_bookmark(title="Own Bookmark")
        other_bookmark = self.setup_bookmark(title="Other Bookmark", user=other_user)

        response = self.client.get(reverse("linkding:bundles.preview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Found 1 bookmarks matching this bundle")
        self.assertContains(response, own_bookmark.title)
        self.assertNotContains(response, other_bookmark.title)
