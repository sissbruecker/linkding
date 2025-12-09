import logging
from typing import List, Optional, Tuple

from django.contrib.auth.models import User
from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, Field

from bookmarks.models import Bookmark

logger = logging.getLogger(__name__)


class TagSuggestions(BaseModel):
    """Pydantic model for structured outputs"""

    tags: List[str] = Field(
        description="List of relevant tags from the allowed vocabulary"
    )


def is_ai_auto_tagging_enabled(user: User) -> bool:
    """
    Check if AI auto-tagging is enabled for the user.

    Returns True if the user has provided necessary AI configuration.
    """
    if not user.is_authenticated:
        return False

    profile = user.profile
    has_api_key = bool(profile.ai_api_key and profile.ai_api_key.strip())
    has_vocabulary = bool(
        profile.ai_tag_vocabulary and profile.ai_tag_vocabulary.strip()
    )
    has_base_url = bool(profile.ai_base_url and profile.ai_base_url.strip())
    has_model = bool(profile.ai_model and profile.ai_model.strip())

    if has_base_url:
        return has_vocabulary and has_model

    return has_api_key and has_vocabulary and has_model


def parse_tag_vocabulary(vocabulary_text: str) -> List[str]:
    """
    Parse newline-separated tag vocabulary into a list of normalized tags.

    Args:
        vocabulary_text: Newline-separated list of tags

    Returns:
        List of normalized (lowercase, stripped) tags without duplicates
    """
    if not vocabulary_text or not vocabulary_text.strip():
        return []

    tags = []
    seen = set()

    for line in vocabulary_text.strip().split("\n"):
        tag = line.strip().lower()
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)

    return tags


def get_ai_tags(bookmark: Bookmark, user: User) -> List[str]:
    """
    Get AI-suggested tags for a bookmark using structured outputs.

    Args:
        bookmark: The bookmark to tag
        user: The user requesting the tagging

    Returns:
        List of suggested tag names (lowercase), empty list on error
    """
    try:
        profile = user.profile

        # Parse allowed tags
        allowed_tags = parse_tag_vocabulary(profile.ai_tag_vocabulary)
        if not allowed_tags:
            logger.warning(
                f"AI auto-tagging skipped - empty vocabulary for user {user.username}"
            )
            return []

        # Build prompt with bookmark metadata
        system_prompt = f"""
You are a tag-assignment assistant. Your job is to map a single bookmark (URL, title, description) to the most relevant tags only from the provided allowed-tags list. Follow these rules exactly:
- Only choose tags from the allowed_tags list. Do not invent or modify tags. Output tag names exactly as they appear in allowed_tags.
- Return tags ordered from most relevant to least relevant.
- By default, return up to 5 tags. If the bookmark clearly needs more or fewer tags, adjust but do not exceed 8 tags.
- Prefer specific tags over broad ones when both apply.
Be concise, deterministic, and avoid speculation beyond the bookmark content.
"""

        user_prompt = f"""
URL: {bookmark.url}
Title: {bookmark.title or "N/A"}
Description: {bookmark.description or "N/A"}

Allowed tags: {', '.join(allowed_tags)}
"""

        base_url = profile.ai_base_url.strip() if profile.ai_base_url else None
        ai_api_key = profile.ai_api_key.strip() if profile.ai_api_key else "apikey"

        if base_url:
            client = OpenAI(api_key=ai_api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=ai_api_key)

        response = client.chat.completions.parse(
            model=profile.ai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=TagSuggestions,
        )

        # Extract and validate suggested tags
        suggested = response.choices[0].message.parsed

        if not suggested or not suggested.tags:
            return []

        # Double-check that suggested tags are in allowed vocabulary (safety)
        allowed_tags_set = set(allowed_tags)
        validated_tags = [
            tag.lower() for tag in suggested.tags if tag.lower() in allowed_tags_set
        ]

        logger.info(f"AI tags for bookmark {bookmark.id}: {validated_tags}")
        return validated_tags

    except AuthenticationError as e:
        logger.error(
            f"AI authentication failed for user {user.username}: {e}",
            exc_info=False,
        )
        return []
    except RateLimitError as e:
        logger.warning(
            f"AI rate limit hit for user {user.username}: {e}", exc_info=False
        )
        # Re-raise to trigger Huey retry
        raise
    except APIConnectionError as e:
        logger.error(
            f"AI connection error for bookmark {bookmark.id}: {e}", exc_info=False
        )
        # Re-raise to trigger Huey retry for transient network errors
        raise
    except APIError as e:
        logger.error(f"AI API error for bookmark {bookmark.id}: {e}", exc_info=False)
        # Re-raise to trigger Huey retry for transient errors
        if e.status_code and e.status_code >= 500:
            raise
        return []
    except Exception as e:
        logger.error(
            f"Unexpected error during AI auto-tagging for bookmark {bookmark.id}: {e}",
            exc_info=True,
        )
        return []


def list_ai_models(api_key: str, base_url: Optional[str] = None):
    """
    List available AI models.

    Args:
        api_key: The AI API key to use
        base_url: Optional base URL for the API endpoint

    Returns:
        List of available models
    """
    if base_url:
        client = OpenAI(api_key=api_key, base_url=base_url)
    else:
        client = OpenAI(api_key=api_key)
    return client.models.list()


def validate_api_key(
    api_key: str, base_url: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate an AI API key by making a test request. Skips validation if a custom base_url is provided.

    Args:
        api_key: The API key to validate
        base_url: Optional base URL for the API endpoint

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Skip validation when using custom base_url
    if base_url:
        return True, None

    if not api_key or not api_key.strip():
        return False, "API key cannot be empty"

    try:
        list_ai_models(api_key, base_url)
        return True, None
    except AuthenticationError:
        return False, "Invalid API key. Please check your AI API key."
    except APIError as e:
        return False, f"AI API error: {e.message}"
    except Exception as e:
        return False, f"Error validating API key: {str(e)}"
