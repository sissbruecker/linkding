from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from bookmarks.utils import (
    humanize_absolute_date,
    humanize_relative_date,
    normalize_url,
    parse_timestamp,
)


class UtilsTestCase(TestCase):
    def test_humanize_absolute_date(self):
        test_cases = [
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2023, 1, 1),
                "01/01/2021",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 2, 1),
                "01/01/2021",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 1, 8),
                "01/01/2021",
            ),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 7), "Friday"),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 1, 7, 23, 59),
                "Friday",
            ),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 3), "Friday"),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 2), "Yesterday"),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 1, 2, 23, 59),
                "Yesterday",
            ),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 1), "Today"),
        ]

        for test_case in test_cases:
            result = humanize_absolute_date(test_case[0], test_case[1])
            self.assertEqual(test_case[2], result)

    def test_humanize_absolute_date_should_use_current_date_as_default(self):
        with patch.object(timezone, "now", return_value=timezone.datetime(2021, 1, 1)):
            self.assertEqual(
                humanize_absolute_date(timezone.datetime(2021, 1, 1)), "Today"
            )

        # Regression: Test that subsequent calls use current date instead of cached date (#107)
        with patch.object(timezone, "now", return_value=timezone.datetime(2021, 1, 13)):
            self.assertEqual(
                humanize_absolute_date(timezone.datetime(2021, 1, 13)), "Today"
            )

    def test_humanize_relative_date(self):
        test_cases = [
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2022, 1, 1),
                "1 year ago",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2022, 12, 31),
                "1 year ago",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2023, 1, 1),
                "2 years ago",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2023, 12, 31),
                "2 years ago",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 12, 31),
                "11 months ago",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 2, 1),
                "1 month ago",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 1, 31),
                "4 weeks ago",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 1, 14),
                "1 week ago",
            ),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 1, 8),
                "1 week ago",
            ),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 7), "Friday"),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 1, 7, 23, 59),
                "Friday",
            ),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 3), "Friday"),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 2), "Yesterday"),
            (
                timezone.datetime(2021, 1, 1),
                timezone.datetime(2021, 1, 2, 23, 59),
                "Yesterday",
            ),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 1), "Today"),
        ]

        for test_case in test_cases:
            result = humanize_relative_date(test_case[0], test_case[1])
            self.assertEqual(test_case[2], result)

    def test_humanize_relative_date_should_use_current_date_as_default(self):
        with patch.object(timezone, "now", return_value=timezone.datetime(2021, 1, 1)):
            self.assertEqual(
                humanize_relative_date(timezone.datetime(2021, 1, 1)), "Today"
            )

        # Regression: Test that subsequent calls use current date instead of cached date (#107)
        with patch.object(timezone, "now", return_value=timezone.datetime(2021, 1, 13)):
            self.assertEqual(
                humanize_relative_date(timezone.datetime(2021, 1, 13)), "Today"
            )

    def verify_timestamp(self, date, factor=1):
        timestamp_string = str(int(date.timestamp() * factor))
        parsed_date = parse_timestamp(timestamp_string)
        self.assertEqual(date, parsed_date)

    def test_parse_timestamp_fails_for_invalid_timestamps(self):
        with self.assertRaises(ValueError):
            parse_timestamp("invalid")

    def test_parse_timestamp_parses_millisecond_timestamps(self):
        now = timezone.now().replace(microsecond=0)
        self.verify_timestamp(now)

    def test_parse_timestamp_parses_microsecond_timestamps(self):
        now = timezone.now().replace(microsecond=0)
        self.verify_timestamp(now, 1000)

    def test_parse_timestamp_parses_nanosecond_timestamps(self):
        now = timezone.now().replace(microsecond=0)
        self.verify_timestamp(now, 1000000)

    def test_parse_timestamp_fails_for_out_of_range_timestamp(self):
        now = timezone.now().replace(microsecond=0)

        with self.assertRaises(ValueError):
            self.verify_timestamp(now, 1000000000)

    def test_normalize_url_trailing_slash_handling(self):
        test_cases = [
            ("https://example.com/", "https://example.com"),
            (
                "https://example.com/path/",
                "https://example.com/path",
            ),
            ("https://example.com/path/to/page/", "https://example.com/path/to/page"),
            (
                "https://example.com/path",
                "https://example.com/path",
            ),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_query_parameters(self):
        test_cases = [
            ("https://example.com?z=1&a=2", "https://example.com?a=2&z=1"),
            ("https://example.com?c=3&b=2&a=1", "https://example.com?a=1&b=2&c=3"),
            ("https://example.com?param=value", "https://example.com?param=value"),
            ("https://example.com?", "https://example.com"),
            (
                "https://example.com?empty=&filled=value",
                "https://example.com?empty=&filled=value",
            ),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_case_sensitivity(self):
        test_cases = [
            (
                "https://EXAMPLE.com/Path/To/Page",
                "https://example.com/Path/To/Page",
            ),
            ("https://EXAMPLE.COM/API/v1/Users", "https://example.com/API/v1/Users"),
            (
                "HTTPS://EXAMPLE.COM/path",
                "https://example.com/path",
            ),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_special_characters_and_encoding(self):
        test_cases = [
            (
                "https://example.com/path%20with%20spaces",
                "https://example.com/path%20with%20spaces",
            ),
            ("https://example.com/caf%C3%A9", "https://example.com/caf%C3%A9"),
            (
                "https://example.com/path?q=hello%20world",
                "https://example.com/path?q=hello%20world",
            ),
            ("https://example.com/pàth", "https://example.com/pàth"),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_various_protocols(self):
        test_cases = [
            ("FTP://example.com", "ftp://example.com"),
            ("HTTP://EXAMPLE.COM", "http://example.com"),
            ("https://example.com", "https://example.com"),
            ("file:///path/to/file", "file:///path/to/file"),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_port_handling(self):
        test_cases = [
            ("https://example.com:8080", "https://example.com:8080"),
            ("https://EXAMPLE.COM:8080", "https://example.com:8080"),
            ("http://example.com:80", "http://example.com:80"),
            ("https://example.com:443", "https://example.com:443"),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_authentication_handling(self):
        test_cases = [
            ("https://user:pass@EXAMPLE.COM", "https://user:pass@example.com"),
            ("https://user@EXAMPLE.COM", "https://user@example.com"),
            ("ftp://admin:secret@EXAMPLE.COM", "ftp://admin:secret@example.com"),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_fragment_handling(self):
        test_cases = [
            ("https://example.com#", "https://example.com"),
            ("https://example.com#section", "https://example.com#section"),
            ("https://EXAMPLE.COM/path#Section", "https://example.com/path#Section"),
            ("https://EXAMPLE.COM/path/#Section", "https://example.com/path#Section"),
            ("https://example.com?a=1#fragment", "https://example.com?a=1#fragment"),
            (
                "https://example.com?z=2&a=1#fragment",
                "https://example.com?a=1&z=2#fragment",
            ),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_edge_cases(self):
        test_cases = [
            ("", ""),
            ("   ", ""),
            ("   https://example.com   ", "https://example.com"),
            ("not-a-url", "not-a-url"),
            ("://invalid", "://invalid"),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)

    def test_normalize_url_internationalized_domain_names(self):
        test_cases = [
            (
                "https://xn--fsq.xn--0zwm56d",
                "https://xn--fsq.xn--0zwm56d",
            ),
            ("https://测试.中国", "https://测试.中国"),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected.lower() if expected else expected, result)

    def test_normalize_url_complex_query_parameters(self):
        test_cases = [
            (
                "https://example.com?z=1&a=2&z=3&b=4",
                "https://example.com?a=2&b=4&z=1&z=3",  # Multiple values for same key
            ),
            (
                "https://example.com?param=value1&param=value2",
                "https://example.com?param=value1&param=value2",
            ),
            (
                "https://example.com?special=%21%40%23%24%25",
                "https://example.com?special=%21%40%23%24%25",
            ),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                result = normalize_url(original)
                self.assertEqual(expected, result)
