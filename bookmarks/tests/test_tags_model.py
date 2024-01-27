from django.test import TestCase

from bookmarks.models import parse_tag_string


class TagTestCase(TestCase):

    def test_parse_tag_string_returns_list_of_tag_names(self):
        self.assertCountEqual(
            parse_tag_string("book, movie, album"), ["book", "movie", "album"]
        )

    def test_parse_tag_string_respects_separator(self):
        self.assertCountEqual(
            parse_tag_string("book movie album", " "), ["book", "movie", "album"]
        )

    def test_parse_tag_string_orders_tag_names_alphabetically(self):
        self.assertListEqual(
            parse_tag_string("book,movie,album"), ["album", "book", "movie"]
        )
        self.assertListEqual(
            parse_tag_string("Book,movie,album"), ["album", "Book", "movie"]
        )

    def test_parse_tag_string_handles_whitespace(self):
        self.assertCountEqual(
            parse_tag_string("\t  book, movie \t, album, \n\r"),
            ["album", "book", "movie"],
        )

    def test_parse_tag_string_handles_invalid_input(self):
        self.assertListEqual(parse_tag_string(None), [])
        self.assertListEqual(parse_tag_string(""), [])

    def test_parse_tag_string_deduplicates_tag_names(self):
        self.assertEqual(len(parse_tag_string("book,book,Book,BOOK")), 1)

    def test_parse_tag_string_handles_duplicate_separators(self):
        self.assertCountEqual(
            parse_tag_string("book,,movie,,,album"), ["album", "book", "movie"]
        )

    def test_parse_tag_string_replaces_whitespace_within_names(self):
        self.assertCountEqual(
            parse_tag_string("travel guide, book recommendations"),
            ["travel-guide", "book-recommendations"],
        )
