# API

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
      "website_title": "Website title",
      "website_description": "Website description",
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

**Archived**

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

