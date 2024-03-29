from django.urls import reverse

from bookmarks.tests.test_bookmark_details_modal import BookmarkDetailsModalTestCase


class BookmarkDetailsViewTestCase(BookmarkDetailsModalTestCase):
    def get_base_url(self, bookmark):
        return reverse("bookmarks:details", args=[bookmark.id])
