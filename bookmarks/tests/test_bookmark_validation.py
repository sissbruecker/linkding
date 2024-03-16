import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from bookmarks.models import BookmarkForm, Bookmark

User = get_user_model()

ENABLED_URL_VALIDATION_TEST_CASES = [
    ("thisisnotavalidurl", False),
    ("http://domain", False),
    ("unknownscheme://domain.com", False),
    ("http://domain.com", True),
    ("http://www.domain.com", True),
    ("https://domain.com", True),
    ("https://www.domain.com", True),
]

DISABLED_URL_VALIDATION_TEST_CASES = [
    ("thisisnotavalidurl", True),
    ("http://domain", True),
    ("unknownscheme://domain.com", True),
    ("http://domain.com", True),
    ("http://www.domain.com", True),
    ("https://domain.com", True),
    ("https://www.domain.com", True),
]


class BookmarkValidationTestCase(TestCase):

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            "testuser", "test@example.com", "password123"
        )

    def test_bookmark_model_should_not_allow_missing_url(self):
        bookmark = Bookmark(
            date_added=datetime.datetime.now(),
            date_modified=datetime.datetime.now(),
            owner=self.user,
        )

        with self.assertRaises(ValidationError):
            bookmark.full_clean()

    def test_bookmark_model_should_not_allow_empty_url(self):
        bookmark = Bookmark(
            url="",
            date_added=datetime.datetime.now(),
            date_modified=datetime.datetime.now(),
            owner=self.user,
        )

        with self.assertRaises(ValidationError):
            bookmark.full_clean()

    @override_settings(LD_DISABLE_URL_VALIDATION=False)
    def test_bookmark_model_should_validate_url_if_not_disabled_in_settings(self):
        self._run_bookmark_model_url_validity_checks(ENABLED_URL_VALIDATION_TEST_CASES)

    @override_settings(LD_DISABLE_URL_VALIDATION=True)
    def test_bookmark_model_should_not_validate_url_if_disabled_in_settings(self):
        self._run_bookmark_model_url_validity_checks(DISABLED_URL_VALIDATION_TEST_CASES)

    def test_bookmark_form_should_validate_required_fields(self):
        form = BookmarkForm(data={"url": ""})

        self.assertEqual(len(form.errors), 1)
        self.assertIn("required", str(form.errors))

        form = BookmarkForm(data={"url": None})

        self.assertEqual(len(form.errors), 1)
        self.assertIn("required", str(form.errors))

    @override_settings(LD_DISABLE_URL_VALIDATION=False)
    def test_bookmark_form_should_validate_url_if_not_disabled_in_settings(self):
        self._run_bookmark_form_url_validity_checks(ENABLED_URL_VALIDATION_TEST_CASES)

    @override_settings(LD_DISABLE_URL_VALIDATION=True)
    def test_bookmark_form_should_not_validate_url_if_disabled_in_settings(self):
        self._run_bookmark_form_url_validity_checks(DISABLED_URL_VALIDATION_TEST_CASES)

    def _run_bookmark_model_url_validity_checks(self, cases):
        for case in cases:
            url, expectation = case
            bookmark = Bookmark(
                url=url,
                date_added=datetime.datetime.now(),
                date_modified=datetime.datetime.now(),
                owner=self.user,
            )

            try:
                bookmark.full_clean()
                self.assertTrue(expectation, "Did not expect validation error")
            except ValidationError as e:
                self.assertFalse(expectation, "Expected validation error")
                self.assertTrue(
                    "url" in e.message_dict, "Expected URL validation to fail"
                )

    def _run_bookmark_form_url_validity_checks(self, cases):
        for case in cases:
            url, expectation = case
            form = BookmarkForm(data={"url": url})

            if expectation:
                self.assertEqual(len(form.errors), 0)
            else:
                self.assertEqual(len(form.errors), 1)
                self.assertIn("Enter a valid URL", str(form.errors))
