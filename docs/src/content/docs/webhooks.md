---
title: "Webhooks"
description: "How to notify other applications about bookmark changes using webhooks"
---

Webhooks allow other applications to react to changes to your bookmarks, for example to post new bookmarks to a chat, trigger an automation in tools like n8n or Home Assistant, or sync bookmarks to another service.
Each user can register webhooks in the *Settings > Integrations* page.
When an event occurs that a webhook is subscribed to, linkding sends a `POST` request with a JSON payload to the webhook's URL.

## Events

The following events are available:

| Event                 | Sent when                                                                                  |
|-----------------------|--------------------------------------------------------------------------------------------|
| `bookmark.created`    | A bookmark is added                                                                        |
| `bookmark.updated`    | Any data of a bookmark other than its archive state changes, see the list below            |
| `bookmark.deleted`    | A bookmark is deleted                                                                      |
| `bookmark.archived`   | A bookmark that was not archived is archived                                               |
| `bookmark.unarchived` | A bookmark that was archived is unarchived                                                 |

Events describe how the data of a bookmark changed, not which action caused the change.
linkding compares each affected bookmark before and after an operation, and sends events for the differences, no matter whether the change was made in the web interface, the REST API, the browser extension, the admin panel, or by a background task.
This means that:

- Each affected bookmark gets its own message, including for bulk actions.
- Actions that do not change anything send no events, for example archiving a bookmark that is already archived, marking a read bookmark as read, or saving a bookmark without making changes.
- A change that affects multiple aspects of a bookmark sends an event for each of them. For example, editing the title of a bookmark and archiving it at the same time sends both `bookmark.updated` and `bookmark.archived`, both with the same, final bookmark data.
- Changes to tags are reported for every bookmark that has the tag. Renaming or deleting a tag, or merging tags, sends `bookmark.updated` for each bookmark whose tags change.
- Importing bookmarks from a file sends `bookmark.created` for new bookmarks, and `bookmark.updated` for existing bookmarks that changed. Large imports can send many messages.
- Updates made by background tasks are reported as well, such as refreshing the title and description of a bookmark, or adding the link to a snapshot on the Internet Archive.
- Moving a bookmark to another user in the admin panel is reported as `bookmark.deleted` to the previous owner, and as `bookmark.created` to the new owner.

`bookmark.updated` is sent when any of these fields change: `url`, `title`, `description`, `notes`, `web_archive_snapshot_url`, `unread`, `shared`, `tag_names` and `date_added`.
Changes to data that is not part of the payload, such as favicons, preview images, or HTML snapshots and other files attached to a bookmark, do not send events.
The modification date alone does not count as a change either.

## Payload

The request body is a JSON object that contains the event type, the time the event occurred, and the bookmark data at that time.
The bookmark data uses the same format as the [REST API](/api), except that it does not include favicon and preview image URLs.
For `bookmark.deleted` events, it contains the bookmark as it was before it was deleted.

```json
{
  "type": "bookmark.created",
  "timestamp": "2026-09-29T10:15:04.187536Z",
  "data": {
    "id": 1,
    "url": "https://example.com",
    "title": "Example title",
    "description": "Example description",
    "notes": "Example notes",
    "web_archive_snapshot_url": "",
    "is_archived": false,
    "unread": false,
    "shared": false,
    "tag_names": [
      "tag1",
      "tag2"
    ],
    "date_added": "2026-09-29T10:15:04.123456Z",
    "date_modified": "2026-09-29T10:15:04.123456Z"
  }
}
```

The *Test* button next to a webhook sends a message with the type `webhook.test`, which can be used to check whether the webhook can be reached:

```json
{
  "type": "webhook.test",
  "timestamp": "2026-09-29T10:15:04.187536Z",
  "data": {
    "message": "This is a test message from linkding."
  }
}
```

## Verifying signatures

Each webhook has a secret that is used to sign messages, so that the receiver can verify that a message was sent by linkding and was not modified.
The secret is only shown once when creating the webhook. If you lose it, delete the webhook and create a new one.

Signatures follow the [Standard Webhooks](https://www.standardwebhooks.com/) specification, so you can use one of the [existing libraries](https://github.com/standard-webhooks/standard-webhooks/tree/main/libraries) to verify them.
Each request contains the following headers:

- `webhook-id`: A unique ID for the message. It stays the same when a delivery is retried, so it can be used to ignore duplicate messages.
- `webhook-timestamp`: The time of the delivery attempt, as a Unix timestamp in seconds.
- `webhook-signature`: The signature, prefixed with the version identifier `v1,`.

The signature is the base64 encoded HMAC-SHA256 of the message ID, the timestamp and the raw request body, joined by dots (`{id}.{timestamp}.{body}`).
The key is the part of the secret after the `whsec_` prefix, decoded from base64.
To protect against replay attacks, receivers should also reject messages with a timestamp that is too far in the past.

An example of verifying a message in Python without additional libraries:

```python
import base64
import hashlib
import hmac
import time


def verify(secret: str, headers: dict, body: bytes) -> bool:
    message_id = headers["webhook-id"]
    timestamp = headers["webhook-timestamp"]
    if abs(time.time() - int(timestamp)) > 5 * 60:
        return False

    key = base64.b64decode(secret.removeprefix("whsec_"))
    content = f"{message_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, content, hashlib.sha256).digest()).decode()

    # The header can contain multiple space-separated signatures
    signatures = headers["webhook-signature"].split(" ")
    return any(
        hmac.compare_digest(expected, signature.removeprefix("v1,"))
        for signature in signatures
    )
```

## Delivery and retries

Messages are sent by linkding's background task processor, so webhooks do not work if background tasks are disabled using the [`LD_DISABLE_BACKGROUND_TASKS`](/options#ld_disable_background_tasks) option.
A delivery is considered successful if the webhook responds with a `2xx` status code within 10 seconds.
Redirects are not followed.

If a delivery fails, it is retried up to five times, after about 1 minute, 4 minutes, 16 minutes, 1 hour and 4 hours.
The *Integrations* settings page shows the result of the latest delivery for each webhook.
Disabling or deleting a webhook also cancels any retries that are still pending.

## Guarantees

linkding makes the following guarantees about messages, which receivers can rely on:

- **Every change is reported.** Every change to the data in the payload that linkding makes results in messages to all enabled webhooks that are subscribed to the resulting events. This includes changes made in the web interface, the REST API, the browser extension, the admin panel, by importing bookmarks, and by background tasks. See below for the exceptions.
- **Only saved changes are reported.** Messages are queued once a change has been saved. A receiver that calls the REST API in response sees the new state, or a later one. If an operation fails, no messages are sent for it.
- **Messages contain the complete state.** Each message contains all data of the bookmark after the change, or before the deletion for `bookmark.deleted`. Receivers do not need to combine messages to know the state of a bookmark. The only exception is `date_modified`, which can be updated without sending a message, as it does not count as a change on its own.
- **Timestamps order changes.** The `timestamp` in the payload is the time of the change. For a given bookmark, a message with a later timestamp always reflects a later state. This requires that the clocks of all linkding processes are in sync, which is the case when running linkding in a single container, as usual. Messages for the events of a single operation, for example `bookmark.updated` and `bookmark.archived` for an edit that also archives the bookmark, share the same timestamp and data.
- **Concurrent changes are reported correctly.** When multiple changes to the same bookmark happen at the same time, for example from two browser tabs or devices, or by a user and a background task, each change is compared against the result of the previous one. The same change is never reported twice.

The following is **not** guaranteed:

- **Order.** Messages are delivered independently of each other, and retries can deliver a message after newer ones. Receivers should remember the `timestamp` of the latest message they processed for each bookmark, and ignore messages with an older timestamp. Messages with the same timestamp belong to the same change, and should not be ignored. This includes deleted bookmarks, so that a delayed `bookmark.updated` message does not restore a bookmark that was deleted.
- **Exactly-once delivery.** A message may be delivered more than once, for example when a webhook processes a message, but does not respond within the timeout. Use the `webhook-id` header to ignore messages that were already processed. It is unique for each message, and the same for all delivery attempts of a message.

Note that the `webhook-timestamp` header is the time of the delivery attempt, which is used for verifying signatures, not the time of the change.

### When changes are not reported

Messages are not sent in these cases:

- Background tasks are disabled using the [`LD_DISABLE_BACKGROUND_TASKS`](/options#ld_disable_background_tasks) option.
- The webhook is disabled, or does not exist yet, when the change is made. Messages are not sent retroactively after enabling a webhook.
- The webhook is disabled or deleted before a queued message is delivered.
- A delivery still fails after all retries.
- The changed data is not part of the payload, as described in [Events](#events).
- The change is made outside of linkding, for example by editing the database directly, or restoring a backup.
- A user is deleted in the admin panel. This deletes their bookmarks, but also their webhooks.
- linkding fails to determine the changes due to an unexpected error. The change itself still succeeds, the error is logged.

## Webhooks on internal networks

To protect against server-side request forgery, linkding does not send requests to hosts on internal networks by default.
This includes the server linkding runs on, other Docker containers, and hosts on your local network.
If you want to use a webhook that points to such a host, for example a self-hosted automation tool, allow it with the [`LD_ALLOWED_INTERNAL_HOSTS`](/options#ld_allowed_internal_hosts) option.
