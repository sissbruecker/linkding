import logging
import requests

from typing import Literal, TypedDict, List
from requests.auth import HTTPBasicAuth
from bookmarks.models import Bookmark, User

logger = logging.getLogger(__name__)

webhook_options = Literal[
    "new_bookmark",
    "updated_bookmark",
    "deleted_bookmark"]

class WebhookBookmarkPayload(TypedDict):
    url: str
    id: int
    user: str
    title: str
    description: str
    notes: str
    website_title: str
    website_description: str
    date_added: str
    tags: List[str]


def send_webhook(
    current_user: User,
    event: webhook_options,
    new_bookmark: Bookmark,
    old_bookmark: Bookmark = None,
):
    wehbook_tag = current_user.profile.webhook_tag
    
    if event == "new_bookmark":
        has_to_send_webhook = new_bookmark.tags.filter(name=wehbook_tag).exists()
    else:
        has_to_send_webhook = old_bookmark.tags.filter(name=wehbook_tag).exists()
        
    has_webhook_enabled = current_user.profile.webhook_enabled
    webhook_url = current_user.profile.webhook_url

    if not (has_webhook_enabled and has_to_send_webhook):
        return
    if not webhook_url:
        return

    basic_auth_username = current_user.profile.webhook_auth_username
    basic_auth_password = current_user.profile.webhook_auth_password

    basic_auth = HTTPBasicAuth(basic_auth_username, basic_auth_password)

    headers = {'User-Agent': 'Linkding'}
    response = None

    match event:
        case "new_bookmark":
            payload = get_webhook_added_payload(current_user, new_bookmark)
        case "updated_bookmark":
            payload = get_webhook_updated_payload(
                current_user, old_bookmark, new_bookmark)
        case "deleted_bookmark":
            payload = get_webhook_deleted_payload(current_user, old_bookmark)

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            auth=basic_auth,
            timeout=5
        )

        # check for HTTP errors
        response.raise_for_status()

        logger.info(
            f"Successfully sent "'{event}'"  webhook for user '{current_user.username}' "
        )

        return "Success"

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Error sending webhook for user '{current_user.username}' "
            f"to '{webhook_url}'. Error: \"{e}\""
        )
        if response is not None:
            logger.error(
                f"Webhook response status code: {response.status_code}")

        return "Error", str(e)


def get_webhook_payload_from_bookmark(current_user: User, bookmark: Bookmark) -> WebhookBookmarkPayload:
    payload = {
        "url": bookmark.url,
        "id": bookmark.id,
        "user": current_user.username,
        "title": bookmark.title,
        "description": bookmark.description,
        "notes": bookmark.notes,
        "website_title": bookmark.website_title,
        "website_description": bookmark.website_description,
        "date_added": bookmark.date_added.isoformat(),
        "tags": bookmark.tag_names
    }

    return payload


def get_webhook_added_payload(current_user: User, bookmark: Bookmark):
    payload = {
        "event": "new_bookmark",
        "bookmark": get_webhook_payload_from_bookmark(current_user, bookmark)
    }
    return payload


def get_webhook_updated_payload(current_user: User, old_bookmark: Bookmark, new_bookmark: Bookmark):
    payload = {
        "event": "updated_bookmark",
        "old_bookmark": get_webhook_payload_from_bookmark(current_user, old_bookmark),
        "new_bookmark": get_webhook_payload_from_bookmark(current_user, new_bookmark)
    }

    return payload


def get_webhook_deleted_payload(current_user: User, bookmark: Bookmark):
    payload = {
        "event": "deleted_bookmark",
        "bookmark": get_webhook_payload_from_bookmark(current_user, bookmark)
    }

    return payload


class BookmarkTagProxy:
    def __init__(self, bookmark_instance, fixed_tags):
        self._bookmark = bookmark_instance
        self.tag_names = fixed_tags  # Override tag_names attribute

    def __getattr__(self, attr):
        # If the attribute isn't 'tag_names', get it from the real bookmark
        return getattr(self._bookmark, attr)
