from bookmarks.services import auto_tagging
from django.test import TestCase


class AutoTaggingTestCase(TestCase):
    def test_auto_tag_by_domain(self):
        script = """
            example.com example
            test.com test
        """
        url = "https://example.com/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["example"]))

    def test_auto_tag_by_domain_should_add_all_tags(self):
        script = """
            example.com one two three
        """
        url = "https://example.com/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["one", "two", "three"]))

    def test_auto_tag_by_domain_and_path(self):
        script = """
            example.com/one one
            example.com/two two
            test.com test
        """
        url = "https://example.com/one/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["one"]))

    def test_auto_tag_by_domain_and_path_matches_path_ltr(self):
        script = """
            example.com/one one
            example.com/two two
            test.com test
        """
        url = "https://example.com/one/two"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["one"]))

    def test_auto_tag_by_domain_ignores_domain_in_path(self):
        script = """
            example.com example
        """
        url = "https://test.com/example.com"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set([]))

    def test_auto_tag_by_domain_includes_subdomains(self):
        script = """
            example.com example
            test.example.com test
            some.example.com some
        """
        url = "https://test.example.com/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["example", "test"]))

    def test_auto_tag_by_domain_matches_domain_rtl(self):
        script = """
            example.com example
        """
        url = "https://example.com.bad-website.com/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set([]))

    def test_auto_tag_by_domain_ignores_schema(self):
        script = """
            https://example.com/ https
            http://example.com/ http
        """
        url = "http://example.com/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["https", "http"]))

    def test_auto_tag_by_domain_ignores_lines_with_no_tags(self):
        script = """
            example.com
        """
        url = "https://example.com/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set([]))
