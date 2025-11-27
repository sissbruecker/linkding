from unittest.mock import patch, MagicMock

from django.test import TestCase
from openai import AuthenticationError, RateLimitError, APIError

from bookmarks.models import UserProfile
from bookmarks.services.openai_tagger import (
    is_openai_enabled,
    parse_tag_vocabulary,
    get_ai_tags,
    validate_api_key,
    TagSuggestions,
)
from bookmarks.tests.helpers import BookmarkFactoryMixin


class OpenAITaggerTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.user.profile.openai_api_key = "sk-test"
        self.user.profile.openai_tag_vocabulary = "programming\npython"
        self.user.profile.save()

    def test_is_openai_enabled(self):
        # Both configured
        self.assertTrue(is_openai_enabled(self.user))

        # Missing API key
        self.user.profile.openai_api_key = ""
        self.assertFalse(is_openai_enabled(self.user))

        # Missing vocabulary
        self.user.profile.openai_api_key = "sk-test"
        self.user.profile.openai_tag_vocabulary = ""
        self.assertFalse(is_openai_enabled(self.user))

        # Both missing
        self.user.profile.openai_api_key = ""
        self.assertFalse(is_openai_enabled(self.user))

    def test_parse_tag_vocabulary(self):
        # Normal case
        vocab = "programming\npython\ndjango"
        expected = ["programming", "python", "django"]
        self.assertEqual(parse_tag_vocabulary(vocab), expected)

        # Whitespace and empty lines
        vocab = "  programming  \n\n python \ndjango "
        expected = ["programming", "python", "django"]
        self.assertEqual(parse_tag_vocabulary(vocab), expected)

        # Duplicates
        vocab = "programming\nprogramming\npython"
        expected = ["programming", "python"]
        self.assertEqual(parse_tag_vocabulary(vocab), expected)

        # Case normalization
        vocab = "prograMMing\nPYthon"
        expected = ["programming", "python"]
        self.assertEqual(parse_tag_vocabulary(vocab), expected)

        # Empty input
        self.assertEqual(parse_tag_vocabulary(""), [])
        self.assertEqual(parse_tag_vocabulary(None), [])

    @patch("bookmarks.services.openai_tagger.OpenAI")
    def test_validate_api_key(self, mock_openai):
        # Success
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        is_valid, error = validate_api_key("sk-test")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        mock_client.models.list.assert_called_once()

        # Empty key
        is_valid, error = validate_api_key("")
        self.assertFalse(is_valid)
        self.assertEqual(error, "API key cannot be empty")

        # Authentication error
        mock_client.models.list.side_effect = AuthenticationError(
            "Invalid key", response=MagicMock(), body={}
        )
        is_valid, error = validate_api_key("sk-test")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Invalid API key. Please check your OpenAI API key.")

        # API error
        mock_client.models.list.side_effect = APIError(
            "Server error", request=MagicMock(), body={}
        )
        is_valid, error = validate_api_key("sk-test")
        self.assertFalse(is_valid)
        self.assertIn("OpenAI API error", error)

        # Generic exception
        mock_client.models.list.side_effect = Exception("Something went wrong")
        is_valid, error = validate_api_key("sk-test")
        self.assertFalse(is_valid)
        self.assertIn("Error validating API key", error)

    @patch("bookmarks.services.openai_tagger.OpenAI")
    def test_get_ai_tags(self, mock_openai):
        bookmark = self.setup_bookmark(
            url="https://example.com",
            title="Title",
            description="Description",
        )

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.output_parsed = TagSuggestions(tags=["programming"])
        mock_client.responses.parse.return_value = mock_response

        tags = get_ai_tags(bookmark, self.user)

        self.assertEqual(tags, ["programming"])

        # Verify OpenAI call
        mock_client.responses.parse.assert_called_once()
        call_kwargs = mock_client.responses.parse.call_args[1]
        self.assertEqual(call_kwargs["model"], "gpt-5-nano")
        self.assertEqual(call_kwargs["text_format"], TagSuggestions)

        # Verify prompt contains bookmark info
        messages = call_kwargs["input"]
        user_prompt = messages[1]["content"]
        self.assertIn(bookmark.url, user_prompt)
        self.assertIn(bookmark.title, user_prompt)
        self.assertIn(bookmark.description, user_prompt)

    @patch("bookmarks.services.openai_tagger.OpenAI")
    def test_get_ai_tags_filters_hallucinated_tags(self, mock_openai):
        bookmark = self.setup_bookmark()
        # Update vocabulary to only include 'programming', not 'python'
        self.user.profile.openai_tag_vocabulary = "programming"
        self.user.profile.save()

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # AI returns a tag not in vocabulary
        mock_response = MagicMock()
        mock_response.output_parsed = TagSuggestions(tags=["programming", "python"])
        mock_client.responses.parse.return_value = mock_response

        tags = get_ai_tags(bookmark, self.user)

        # Should only return 'programming' because 'python' is not in user's vocabulary
        self.assertEqual(tags, ["programming"])

    @patch("bookmarks.services.openai_tagger.OpenAI")
    def test_get_ai_tags_empty_vocabulary(self, mock_openai):
        bookmark = self.setup_bookmark()
        self.user.profile.openai_tag_vocabulary = ""
        self.user.profile.save()

        tags = get_ai_tags(bookmark, self.user)

        self.assertEqual(tags, [])
        mock_openai.assert_not_called()

    @patch("bookmarks.services.openai_tagger.OpenAI")
    def test_get_ai_tags_api_errors(self, mock_openai):
        bookmark = self.setup_bookmark()
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Authentication error
        mock_client.responses.parse.side_effect = AuthenticationError(
            "Auth failed", response=MagicMock(), body={}
        )
        self.assertEqual(get_ai_tags(bookmark, self.user), [])

        # API error 500+ (should raise)
        error_500 = APIError("Server error", request=MagicMock(), body={})
        error_500.status_code = 500
        mock_client.responses.parse.side_effect = error_500
        with self.assertRaises(APIError):
            get_ai_tags(bookmark, self.user)

        # API error 400 (should return empty)
        error_400 = APIError("Bad request", request=MagicMock(), body={})
        error_400.status_code = 400
        mock_client.responses.parse.side_effect = error_400
        self.assertEqual(get_ai_tags(bookmark, self.user), [])
