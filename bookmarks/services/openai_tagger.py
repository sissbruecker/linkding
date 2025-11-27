import logging
from typing import List, Optional, Tuple

from django.contrib.auth.models import User
from openai import OpenAI, APIError, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field

from bookmarks.models import Bookmark

logger = logging.getLogger(__name__)


class TagSuggestions(BaseModel):
    """Pydantic model for OpenAI structured outputs"""

    tags: List[str] = Field(
        description="List of relevant tags from the allowed vocabulary"
    )


def is_openai_enabled(user: User) -> bool:
    """
    Check if AI auto-tagging is enabled for the user.

    Returns True if both API Key and tag vocabulary are configured.
    """
    if not user.is_authenticated:
        return False

    profile = user.profile
    has_api_key = bool(profile.openai_api_key and profile.openai_api_key.strip())
    has_vocabulary = bool(
        profile.openai_tag_vocabulary and profile.openai_tag_vocabulary.strip()
    )
    return has_api_key and has_vocabulary


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
    Get AI-suggested tags for a bookmark using OpenAI's structured outputs.

    Args:
        bookmark: The bookmark to tag
        user: The user requesting the tagging

    Returns:
        List of suggested tag names (lowercase), empty list on error
    """
    try:
        profile = user.profile

        # Parse allowed tags
        allowed_tags = parse_tag_vocabulary(profile.openai_tag_vocabulary)
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

        # Call OpenAI with structured outputs
        client = OpenAI(api_key=profile.openai_api_key)

        response = client.responses.parse(
            model=profile.openai_model or "gpt-5-nano",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=TagSuggestions,
        )

        # Extract and validate suggested tags
        suggested = response.output_parsed

        if not suggested or not suggested.tags:
            return []

        # Double-check that suggested tags are in allowed vocabulary (safety)
        allowed_tags_set = set(allowed_tags)
        validated_tags = [
            tag.lower() for tag in suggested.tags if tag.lower() in allowed_tags_set
        ]

        logger.info(
            f"OpenAI suggested tags for bookmark {bookmark.id}: {validated_tags}"
        )
        return validated_tags

    except AuthenticationError as e:
        logger.error(
            f"OpenAI authentication failed for user {user.username}: {e}",
            exc_info=False,
        )
        return []
    except RateLimitError as e:
        logger.warning(
            f"OpenAI rate limit hit for user {user.username}: {e}", exc_info=False
        )
        # Re-raise to trigger Huey retry
        raise
    except APIError as e:
        logger.error(
            f"OpenAI API error for bookmark {bookmark.id}: {e}", exc_info=False
        )
        # Re-raise to trigger Huey retry for transient errors
        if e.status_code and e.status_code >= 500:
            raise
        return []
    except Exception as e:
        logger.error(
            f"Unexpected error during OpenAI tagging for bookmark {bookmark.id}: {e}",
            exc_info=True,
        )
        return []


def list_openai_models(api_key: str):
    """
    List available OpenAI models.

    Args:
        api_key: The OpenAI API key to use

    Returns:
        List of available models
    """
    client = OpenAI(api_key=api_key)
    return client.models.list()


def validate_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an OpenAI API key by making a test request.

    Args:
        api_key: The API key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not api_key or not api_key.strip():
        return False, "API key cannot be empty"

    try:
        list_openai_models(api_key)
        return True, None
    except AuthenticationError:
        return False, "Invalid API key. Please check your OpenAI API key."
    except APIError as e:
        return False, f"OpenAI API error: {e.message}"
    except Exception as e:
        return False, f"Error validating API key: {str(e)}"
