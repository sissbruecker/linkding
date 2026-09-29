"""
Outbound webhooks for bookmark events.

Users can register webhooks that are called when bookmarks are created,
updated, deleted, archived or unarchived. Messages are signed following the
Standard Webhooks specification (https://www.standardwebhooks.com), so that
receivers can verify them with one of the existing libraries:

- webhook-id: unique message ID, stays the same when a delivery is retried
- webhook-timestamp: unix timestamp of the delivery attempt
- webhook-signature: "v1," followed by the base64 encoded HMAC-SHA256 of
  "{id}.{timestamp}.{body}", keyed with the base64 decoded secret without its
  "whsec_" prefix

Events are derived by comparing the state of bookmarks before and after a
change, see get_change_events. Message bodies are created when a change occurs,
so that they reflect the state of the bookmark at that point in time, and so
that they are still available for deleted bookmarks. Tracking changes, queuing
and retrying deliveries is handled in bookmarks.services.tasks.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import serializers

from bookmarks.models import Bookmark, Webhook
from bookmarks.services import http_client
from bookmarks.utils import app_version

logger = logging.getLogger(__name__)

EVENT_TEST = "webhook.test"
DELIVERY_TIMEOUT = 10
SECRET_PREFIX = "whsec_"

_date_field = serializers.DateTimeField()


class WebhookDeliveryError(Exception):
    pass


@dataclass
class WebhookMessage:
    webhook_id: int
    message_id: str
    body: str


def sign(secret: str, message_id: str, timestamp: int, body: str) -> str:
    key = base64.b64decode(secret.removeprefix(SECRET_PREFIX))
    content = f"{message_id}.{timestamp}.{body}".encode()
    digest = hmac.new(key, content, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def serialize_bookmark(bookmark: Bookmark) -> dict:
    # Uses the same field names and formats as the REST API, except for URLs
    # to static files, which require the request to build absolute URLs
    return {
        "id": bookmark.id,
        "url": bookmark.url,
        "title": bookmark.title,
        "description": bookmark.description,
        "notes": bookmark.notes,
        "web_archive_snapshot_url": bookmark.web_archive_snapshot_url,
        "is_archived": bookmark.is_archived,
        "unread": bookmark.unread,
        "shared": bookmark.shared,
        "tag_names": bookmark.tag_names,
        "date_added": _date_field.to_representation(bookmark.date_added),
        "date_modified": _date_field.to_representation(bookmark.date_modified),
    }


def serialize_bookmarks(bookmarks: QuerySet) -> list[dict]:
    """
    Serializes the bookmarks of a queryset like serialize_bookmark. Loads plain
    values instead of model instances, as this runs while bookmarks are locked
    for tracking changes, which should be as short as possible.
    """
    rows = list(
        bookmarks.values(
            "id",
            "url",
            "title",
            "description",
            "notes",
            "web_archive_snapshot_url",
            "is_archived",
            "unread",
            "shared",
            "date_added",
            "date_modified",
        )
    )
    tag_names = defaultdict(list)
    tag_relations = Bookmark.tags.through.objects.filter(
        bookmark_id__in=[row["id"] for row in rows]
    ).values_list("bookmark_id", "tag__name")
    for bookmark_id, tag_name in tag_relations:
        tag_names[bookmark_id].append(tag_name)

    return [
        {
            "id": row["id"],
            "url": row["url"],
            "title": row["title"],
            "description": row["description"],
            "notes": row["notes"],
            "web_archive_snapshot_url": row["web_archive_snapshot_url"],
            "is_archived": row["is_archived"],
            "unread": row["unread"],
            "shared": row["shared"],
            "tag_names": sorted(tag_names[row["id"]]),
            "date_added": _date_field.to_representation(row["date_added"]),
            "date_modified": _date_field.to_representation(row["date_modified"]),
        }
        for row in rows
    ]


# Fields that do not count as an update on their own. Archiving is reported
# with separate events, and the modification date is also bumped by operations
# that do not change anything else.
_UPDATE_IGNORED_FIELDS = ("is_archived", "date_modified")


def get_change_events(before: dict | None, after: dict | None) -> list[str]:
    """
    Returns the events for a change of a bookmark, given its serialized state
    before and after the change. None means that the bookmark did not exist.
    A change can result in multiple events, for example an edit that changes
    the title and archives the bookmark results in both an update and an
    archive event. A change that does not modify any data results in no events.
    """
    if before is None and after is None:
        return []
    if before is None:
        return [Webhook.EVENT_BOOKMARK_CREATED]
    if after is None:
        return [Webhook.EVENT_BOOKMARK_DELETED]

    events = []
    if _without_ignored_fields(before) != _without_ignored_fields(after):
        events.append(Webhook.EVENT_BOOKMARK_UPDATED)
    if before["is_archived"] != after["is_archived"]:
        events.append(
            Webhook.EVENT_BOOKMARK_ARCHIVED
            if after["is_archived"]
            else Webhook.EVENT_BOOKMARK_UNARCHIVED
        )
    return events


def _without_ignored_fields(data: dict) -> dict:
    return {
        key: value for key, value in data.items() if key not in _UPDATE_IGNORED_FIELDS
    }


def create_messages(
    user: User, changes: list[tuple[str, dict]], timestamp: datetime | None = None
) -> list[WebhookMessage]:
    """
    Creates messages for a list of (event, bookmark data) pairs, one for each
    webhook of the user that is subscribed to the event.
    """
    webhooks = list(Webhook.objects.filter(owner=user, enabled=True))
    timestamp = timestamp or timezone.now()

    messages = []
    for event, data in changes:
        # Filter events in Python, as SQLite does not support contains lookups
        # on JSON fields. Users are not expected to have many webhooks.
        subscribed_webhooks = [
            webhook for webhook in webhooks if event in webhook.events
        ]
        if not subscribed_webhooks:
            continue
        body = _create_body(event, timestamp, data)
        for webhook in subscribed_webhooks:
            messages.append(WebhookMessage(webhook.id, _create_message_id(), body))

    return messages


def deliver(webhook: Webhook, message_id: str, body: str):
    """
    Sends a message to a webhook and records the outcome on the webhook. Raises
    WebhookDeliveryError or http_client.RequestException if the delivery failed.
    """
    timestamp = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"linkding/{app_version}",
        "webhook-id": message_id,
        "webhook-timestamp": str(timestamp),
        "webhook-signature": sign(webhook.secret, message_id, timestamp, body),
    }

    try:
        # Do not follow redirects, a redirect would resend the payload to a
        # different URL than the one configured by the user
        response = http_client.post(
            webhook.url,
            data=body.encode(),
            headers=headers,
            timeout=DELIVERY_TIMEOUT,
            allow_redirects=False,
        )
    except http_client.RequestException as error:
        _record_delivery(webhook, Webhook.DELIVERY_STATUS_FAILURE, str(error))
        raise

    status_message = f"HTTP {response.status_code}"
    if not 200 <= response.status_code < 300:
        _record_delivery(webhook, Webhook.DELIVERY_STATUS_FAILURE, status_message)
        raise WebhookDeliveryError(f"Webhook responded with {status_message}")

    _record_delivery(webhook, Webhook.DELIVERY_STATUS_SUCCESS, status_message)


def send_test_message(webhook: Webhook):
    """
    Immediately sends a test message to a webhook, regardless of whether it is
    enabled or which events it is subscribed to. Raises the same errors as
    deliver.
    """
    data = {"message": "This is a test message from linkding."}
    body = _create_body(EVENT_TEST, timezone.now(), data)
    deliver(webhook, _create_message_id(), body)


def _create_body(event: str, timestamp, data: dict) -> str:
    return json.dumps(
        {
            "type": event,
            "timestamp": _date_field.to_representation(timestamp),
            "data": data,
        }
    )


def _create_message_id() -> str:
    return f"msg_{uuid.uuid4().hex}"


def _record_delivery(webhook: Webhook, status: str, message: str):
    webhook.last_delivery_date = timezone.now()
    webhook.last_delivery_status = status
    webhook.last_delivery_message = message[:512]
    # Only update delivery fields, to not overwrite changes made by the user
    # while the delivery was in progress. Errors are only logged, raising would
    # retry a delivery that already succeeded, resulting in a duplicate message.
    try:
        Webhook.objects.filter(id=webhook.id).update(
            last_delivery_date=webhook.last_delivery_date,
            last_delivery_status=webhook.last_delivery_status,
            last_delivery_message=webhook.last_delivery_message,
        )
    except Exception:
        logger.exception(f"Failed to record webhook delivery. webhook={webhook.id}")
