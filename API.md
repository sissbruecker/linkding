# API

The application provides a REST API that can be used by 3rd party applications to manage bookmarks.

## Authentication

All requests against the API need to be authorized using an authorization token. The application automatically generates an API token for each user, which can be accessed through the *Settings* page.

The token needs to be passed as `Authorization` header in the HTTP request:

```
Authorization: Token <Token>
```

## Resources

The following resources are available:

### Bookmarks

**List**

```
GET /api/bookmarks/[?q=<search-phrase>]
```

List bookmarks. Use the `q` query param to apply a search filter using the same logic as through the UI. The action uses pagination with a default limit of `100`.

Example response:

```json
{
  "count": 183,
  "next": "http://127.0.0.1:8000/api/bookmarks/?limit=100&offset=100",
  "previous": null,
  "results": [
    {
      "id": 1,
      "url": "https://example.com",
      "title": "Example title",
      "description": "Example description",
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

**Retrieve**

```
GET /api/bookmarks/<id>/
```

Retrieves a single bookmark by ID.

**Create**

```
POST /api/bookmarks/
```

Creates a new bookmark. Tags are simply assigned using their names.

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

**Update**

```
PUT /api/bookmarks/<id>/
```

Updates a bookmark. Tags are simply assigned using their names.

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

**Delete**

```
DELETE /api/bookmarks/<id>/
```

Deletes a bookmark by ID.