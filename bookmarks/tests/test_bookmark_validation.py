from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from bookmarks.models import BookmarkForm, Link

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


class BookmarkFormTest(TestCase):

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            "testuser", "test@example.com", "password123"
        )

    def test_form(self):
        form = BookmarkForm(data={"url": ""})
        self.assertEqual(form.is_valid(), False)

    def test_valid_bookmarkform(self):
        form = BookmarkForm(data={"url": "https://wwvw.example.com"})
        self.assertEqual(form.is_valid(), True)

    def test_commit_save_false_returns_bookmark_with_link(self):
        form = BookmarkForm(data={"url": "https://wwvw.example.com"})
        bookmark = form.save(commit=False)

        self.assertEqual(bookmark.link.pk, None)

    def test_commit_save_false_returns_bookmark_with_existing_link(self):
        url = "https://www.example.com"
        existing_link = Link.objects.create(url=url)
        form = BookmarkForm(data={"url": url})
        bookmark = form.save(commit=False)

        self.assertEqual(bookmark.link.pk, existing_link.pk)


class BookmarkValidationTestCase(TestCase):

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            "testuser", "test@example.com", "password123"
        )

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

    def _run_bookmark_form_url_validity_checks(self, cases):
        for case in cases:
            url, expectation = case
            form = BookmarkForm(data={"url": url})

            if expectation:
                self.assertEqual(len(form.errors), 0)
            else:
                self.assertEqual(len(form.errors), 1)
                self.assertIn("Enter a valid URL", str(form.errors))
