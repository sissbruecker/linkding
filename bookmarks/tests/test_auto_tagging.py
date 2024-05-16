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

    def test_auto_tag_by_domain_work_with_idn_domains(self):
        script = """
            रजिस्ट्री.भारत tag1
        """
        url = "https://www.xn--81bg3cc2b2bk5hb.xn--h2brj9c/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["tag1"]))

        script = """
            xn--81bg3cc2b2bk5hb.xn--h2brj9c tag1
        """
        url = "https://www.रजिस्ट्री.भारत/"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["tag1"]))

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

    def test_auto_tag_by_domain_path_and_qs(self):
        script = """
            example.com/page?a=b tag1     # true, matches a=b
            example.com/page?a=c&c=d tag2 # true, matches both a=c and c=d
            example.com/page?c=d&l=p tag3 # false, l=p doesn't exists
            example.com/page?a=bb tag4    # false bb != b
            example.com/page?a=b&a=c tag5 # true, matches both a=b and a=c
        """
        url = "https://example.com/page/some?z=x&a=b&v=b&c=d&o=p&a=c"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["tag1", "tag2", "tag5"]))

    def test_auto_tag_by_domain_path_and_qs_works_with_encoded_url(self):
        script = """
            example.com/page?a=йцу tag1
            example.com/page?a=%D0%B9%D1%86%D1%83 tag2
        """
        url = "https://example.com/page?a=%D0%B9%D1%86%D1%83"

        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set(["tag1", "tag2"]))
