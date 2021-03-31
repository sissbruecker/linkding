from django.test import TestCase
from django.utils import timezone

from bookmarks.utils import humanize_absolute_date, humanize_relative_date


class UtilsTestCase(TestCase):

    def test_humanize_absolute_date(self):
        test_cases = [
            (timezone.datetime(2021, 1, 1), timezone.datetime(2023, 1, 1), '01/01/2021'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 2, 1), '01/01/2021'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 8), '01/01/2021'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 7), 'Friday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 7, 23, 59), 'Friday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 3), 'Friday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 2), 'Yesterday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 2, 23, 59), 'Yesterday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 1), 'Today'),
        ]

        for test_case in test_cases:
            result = humanize_absolute_date(test_case[0], test_case[1])
            self.assertEqual(test_case[2], result)

    def test_humanize_relative_date(self):
        test_cases = [
            (timezone.datetime(2021, 1, 1), timezone.datetime(2022, 1, 1), 'A year ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2022, 12, 31), 'A year ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2023, 1, 1), '2 years ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2023, 12, 31), '2 years ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 12, 31), '11 months ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 2, 1), 'A month ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 31), '4 weeks ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 14), 'A week ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 8), 'A week ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 7), 'Friday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 7, 23, 59), 'Friday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 3), 'Friday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 2), 'Yesterday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 2, 23, 59), 'Yesterday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 1), 'Today'),
        ]

        for test_case in test_cases:
            result = humanize_relative_date(test_case[0], test_case[1])
            self.assertEqual(test_case[2], result)
