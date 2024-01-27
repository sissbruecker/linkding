from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class AnonymousViewTestCase(TestCase, BookmarkFactoryMixin):
    def assertSharedBookmarksLinkCount(self, response, count):
        url = reverse("bookmarks:shared")
        self.assertContains(
            response,
            f'<a href="{url}" class="btn btn-link">Shared bookmarks</a>',
            count=count,
        )

    def test_publicly_shared_bookmarks_link(self):
        # should not render link if no public shares exist
        user = self.setup_user(enable_sharing=True)
        self.setup_bookmark(user=user, shared=True)

        response = self.client.get(reverse("login"))
        self.assertSharedBookmarksLinkCount(response, 0)

        # should render link if public shares exist
        user.profile.enable_public_sharing = True
        user.profile.save()

        response = self.client.get(reverse("login"))
        self.assertSharedBookmarksLinkCount(response, 1)
