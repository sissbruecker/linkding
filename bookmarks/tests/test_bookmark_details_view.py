from bookmarks.tests.test_bookmark_details_modal import BookmarkDetailsModalTestCase


class BookmarkDetailsViewTestCase(BookmarkDetailsModalTestCase):
    def get_view_name(self):
        return "bookmarks:details"
