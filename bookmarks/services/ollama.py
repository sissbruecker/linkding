import logging
import requests
import random

from bookmarks.models import GlobalSettings
from bookmarks.services.website_loader import WebsiteMetadata

logger = logging.getLogger(__name__)


def generate_tags(metadata: WebsiteMetadata, settings: GlobalSettings) -> list[str]:
    if not settings.ollama_base_api_url or not settings.ollama_model_name:
        return []

    prompt1 = f"""Title: {metadata.title}\nDescription: {metadata.description}\n
You are provided with the title and description of a website.\n
You need to generate 5 tags for it.\n
Output must be in a single line and comma-separated"""

    prompt = f"""
Generate six comma-separated tags for a webpage with the following title and description.
Title: {metadata.title}
Description: {metadata.description}

The tags should be relevant to the project's purpose and functionality.
Output only the six tags, separated by commas in a single line.
    """

    # Log prompt
    logger.debug(f"Ollama prompt: {prompt}")

    payload = {
        "model": settings.ollama_model_name,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "0m",
        "options": {
            "temperature": 0.6,
            "top_k": 90,
            # "num_predict": 100,
            # Generate random seed
            "seed": random.randint(0, 100000),
        }
    }

    try:
        api_response = requests.post(settings.ollama_base_api_url, json=payload, timeout=30)
        api_response.raise_for_status()

        data = api_response.json()
        tags_string = data.get('response', '')  

        if tags_string:
            # Ollama might return tags with newlines or extra spaces
            tags = tags_string.strip().split(',')
            
            # Strip all tags
            tags = [tag.strip() for tag in tags]
            
            # remove empty tags
            tags = [tag for tag in tags if tag]
            
            # Remove duplicate tags
            seen = set()
            tags = [tag for tag in tags if not (tag in seen or seen.add(tag))]

            # if tag has space join the word by -
            tags = [tag.replace(' ', '-') for tag in tags]
        
            return tags

        return []
    except requests.RequestException as e:
        logger.error(f"Failed to generate tags from Ollama API: {e}", exc_info=e)
        return []
