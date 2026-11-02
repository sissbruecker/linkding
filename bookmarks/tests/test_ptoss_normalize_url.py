
from unittest import TestCase

from bookmarks.utils import normalize_url


class TestNormalizeUrlPTOSS(TestCase):

    def test_normalize_url_caixa_preta(self):
        test_cases = [
            ("https://example.com", "https://example.com"),
            ("https://EXAMPLE.COM", "https://example.com"),
            ("HTTPS://example.com", "https://example.com"),
            (
                "https://example.com/path/",
                "https://example.com/path",
            ),
            (
                "https://example.com?z=1&a=2",
                "https://example.com?a=2&z=1",
            ),
            (
                "https://example.com?z=1&a=2&z=3",
                "https://example.com?a=2&z=1&z=3",
            ),
            (
                "https://user:pass@EXAMPLE.COM",
                "https://user:pass@example.com",
            ),
            (
                "https://example.com/path#Section",
                "https://example.com/path#Section",
            ),
            ("FTP://EXAMPLE.COM", "ftp://example.com"),
            (
                "  https://example.com  ",
                "https://example.com",
            ),
            ("", ""),
            ("   ", ""),
            (None, ""),
            (123, ""),
            (
                "https://example.com:abc",
                "https://example.com:abc",
            ),
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                self.assertEqual(
                    expected,
                    normalize_url(original)
                )

    def test_normalize_url_caixa_branca_mcdc(self):
        test_cases = [
            (None, ""),                   # A=V, B=V
            ("", ""),                     # A=V, B=F
            (123, ""),                    # A=F, B=V
            (
                "https://example.com",
                "https://example.com"
            ),                            # A=F, B=F
        ]

        for original, expected in test_cases:
            with self.subTest(url=original):
                self.assertEqual(
                    expected,
                    normalize_url(original)
                )
