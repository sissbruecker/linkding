import unittest

from bookmarks.services.auto_tagging import _domains_matches, get_tags


class DomainBoundaryTDDTest(unittest.TestCase):

    def test_rejects_domain_suffix_without_dot_separator(self):
        self.assertFalse(
            _domains_matches("example.com", "notexample.com")
        )

    def test_does_not_apply_tag_to_unrelated_suffix_domain(self):
        self.assertEqual(
            get_tags(
                "example.com tag-indevida",
                "https://notexample.com/"
            ),
            set()
        )

    def test_exact_domain_still_matches(self):
        self.assertTrue(
            _domains_matches("example.com", "example.com")
        )

    def test_valid_subdomain_still_matches(self):
        self.assertTrue(
            _domains_matches("example.com", "docs.example.com")
        )


if __name__ == "__main__":
    unittest.main()
