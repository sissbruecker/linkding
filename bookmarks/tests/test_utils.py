from django.test import TestCase
from django.utils import timezone

from bookmarks.utils import humanize_time_delta


class UtilsTestCase(TestCase):

    def test_humanize_time_delta(self):
        test_cases = [
            (timezone.datetime(2021, 1, 1), timezone.datetime(2022, 1, 1), 'a year ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2022, 12, 31), 'a year ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2023, 1, 1), '2 years ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2023, 12, 31), '2 years ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 12, 31), '11 months ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 2, 1), 'a month ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 31), '4 weeks ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 14), 'a week ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 8), 'a week ago'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 7), 'Friday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 3), 'Friday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 2), 'yesterday'),
            (timezone.datetime(2021, 1, 1), timezone.datetime(2021, 1, 1), 'today'),
        ]

        for test_case in test_cases:
            result = humanize_time_delta(test_case[0], test_case[1])
            self.assertEqual(test_case[2], result)
