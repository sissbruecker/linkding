---
title: "API"
description: "How to use the REST API of linkding"
---

The application provides a REST API that can be used by 3rd party applications to manage bookmarks.

## Authentication

All requests against the API must be authorized using an authorization token. The application automatically generates an API token for each user, which can be accessed through the *Settings* page.

The token needs to be passed as `Authorization` header in the HTTP request:

```
Authorization: Token <Token>
```

## Resources

The following resources are available:

### Bookmarks

**List**

```
GET /api/bookmarks/
```

List bookmarks.

Parameters:

- `q` - Filters results using a search phrase using the same logic as through the UI
- `limit` - Limits the max. number of results. Default is `100`.
- `offset` - Index from which to start returning results

Example response:

```json
{
  "count": 123,
  "next": "http://127.0.0.1:8000/api/bookmarks/?limit=100&offset=100",
  "previous": null,
  "results": [
    {
      "id": 1,
      "url": "https://example.com",
      "title": "Example title",
      "description": "Example description",
      "notes": "Example notes",
      "web_archive_snapshot_url": "https://web.archive.org/web/20200926094623/https://example.com",
      "favicon_url": "http://127.0.0.1:8000/static/https_example_com.png",
      "preview_image_url": "http://127.0.0.1:8000/static/0ac5c53db923727765216a3a58e70522.jpg",
      "is_archived": false,
      "unread": false,
      "shared": false,
      "tag_names": [
        "tag1",
        "tag2"
      ],
      "date_added": "2020-09-26T09:46:23.006313Z",
      "date_modified": "2020-09-26T16:01:14.275335Z"
    },
    ...
  ]
}
```

**List Archived**

```
GET /api/bookmarks/archived/
```

List archived bookmarks.

Parameters and response are the same as for the regular list endpoint.

**Retrieve**

```
GET /api/bookmarks/<id>/
```

Retrieves a single bookmark by ID.

**Check**

```
GET /api/bookmarks/check/?url=https%3A%2F%2Fexample.com
```

Allows to check if a URL is already bookmarked. If the URL is already bookmarked, the `bookmark` property in the response holds the bookmark data, otherwise it is `null`.

Also returns a `metadata` property that contains metadata scraped from the website. Finally, the `auto_tags` property contains the tag names that would be automatically added when creating a bookmark for that URL.

Example response:

```json
{
  "bookmark": {
    "id": 1,
    "url": "https://example.com",
    "title": "Example title",
    "description": "Example description",
    ...
  },
  "metadata": {
    "title": "Scraped website title",
    "description": "Scraped website description",
    ...
  },
  "auto_tags": [
    "tag1",
    "tag2"
  ]
}
```

**Create**

```
POST /api/bookmarks/
```

Creates a new bookmark. Tags are simply assigned using their names. Including
`is_archived: true` saves a bookmark directly to the archive.

If the provided URL is already bookmarked, this silently updates the existing bookmark instead of creating a new one. If you are implementing a user interface, consider notifying users about this behavior. You can use the `/check` endpoint to check if a URL is already bookmarked and at the same time get the existing bookmark data. This behavior may change in the future to return an error instead.

If the title and description are not provided or empty, the application automatically tries to scrape them from the bookmarked website. This behavior can be disabled by adding the `disable_scraping` query parameter to the API request.

Example payload:

```json
{
  "url": "https://example.com",
  "title": "Example title",
  "description": "Example description",
  "notes": "Example notes",
  "is_archived": false,
  "unread": false,
  "shared": false,
  "tag_names": [
    "tag1",
    "tag2"
  ]
}
```

**Update**

```
PUT /api/bookmarks/<id>/
PATCH /api/bookmarks/<id>/
```

Updates a bookmark.
When using `POST`, at least all required fields must be provided (currently only `url`).
When using `PATCH`, only the fields that should be updated need to be provided.
Regardless which method is used, any field that is not provided is not modified.
Tags are simply assigned using their names.

If the provided URL is already bookmarked this returns an error.

Example payload:

```json
{
  "url": "https://example.com",
  "title": "Example title",
  "description": "Example description",
  "tag_names": [
    "tag1",
    "tag2"
  ]
}
```

**Archive**

```
POST /api/bookmarks/<id>/archive/
```

Archives a bookmark.

**Unarchive**

```
POST /api/bookmarks/<id>/unarchive/
```

Unarchives a bookmark.

**Delete**

```
DELETE /api/bookmarks/<id>/
```

Deletes a bookmark by ID.

### Tags

**List**

```
GET /api/tags/
```

List tags.

Parameters:

- `limit` - Limits the max. number of results. Default is `100`.
- `offset` - Index from which to start returning results

Example response:

```json
{
  "count": 123,
  "next": "http://127.0.0.1:8000/api/tags/?limit=100&offset=100",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "example",
      "date_added": "2020-09-26T09:46:23.006313Z"
    },
    ...
  ]
}
```

**Retrieve**

```
GET /api/tags/<id>/
```

Retrieves a single tag by ID.

**Create**

```
POST /api/tags/
```

Creates a new tag.

Example payload:

```json
{
  "name": "example"
}
```

### User

**Profile**

```
GET /api/user/profile/
```

User preferences.

Example response:

```json
{
  "theme": "auto",
  "bookmark_date_display": "relative",
  "bookmark_link_target": "_blank",
  "web_archive_integration": "enabled",
  "tag_search": "lax",
  "enable_sharing": true,
  "enable_public_sharing": true,
  "enable_favicons": false,
  "display_url": false,
  "permanent_notes": false,
  "search_preferences": {
    "sort": "title_asc",
    "shared": "off",
    "unread": "off"
  }
}
```
