import unittest

from bookmarks.services.auto_tagging import _qs_matches


class QueryStringMatchingPTOSS2Test(unittest.TestCase):

    def test_expected_parameter_exists_with_matching_value(self):
        self.assertTrue(_qs_matches("tema=python", "tema=python"))

    def test_expected_parameter_not_present(self):
        self.assertFalse(_qs_matches("tema=python", "autor=python"))

    def test_expected_value_not_present(self):
        self.assertFalse(_qs_matches("tema=python", "tema=django"))

    def test_expected_blank_value_is_wildcard_when_key_exists(self):
        self.assertTrue(_qs_matches("tema=", "tema=django"))

    def test_expected_blank_value_fails_when_key_missing(self):
        self.assertFalse(_qs_matches("tema=", "autor=django"))

    def test_multiple_expected_values_must_all_match(self):
        self.assertTrue(_qs_matches(
            "tema=python&tema=django",
            "tema=django&tema=python"
        ))
        self.assertFalse(_qs_matches(
            "tema=python&tema=django",
            "tema=python"
        ))

    def test_extra_actual_parameters_are_allowed(self):
        self.assertTrue(_qs_matches(
            "tema=python",
            "autor=a&tema=python&pagina=1"
        ))

    def test_empty_queries_match_each_other(self):
        self.assertTrue(_qs_matches("", ""))

    def test_mcdc_independence_nonempty_condition(self):
        self.assertTrue(_qs_matches("tema=", "tema=django"))
        self.assertFalse(_qs_matches("tema=python", "tema=django"))

    def test_mcdc_independence_membership_condition(self):
        self.assertTrue(_qs_matches("tema=django", "tema=django"))
        self.assertFalse(_qs_matches("tema=python", "tema=django"))


if __name__ == "__main__":
    unittest.main()
