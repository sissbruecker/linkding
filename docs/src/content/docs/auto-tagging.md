---
title: "Auto tagging"
description: "How to automatically assign tags to bookmarks based on predefined rules"
---

Auto tagging allows to automatically add tags to bookmarks based on predefined rules. This makes categorizing commonly
bookmarked websites easier and faster.

Auto tagging rules can be defined in the profile settings. Each rule maps a URL pattern to one or more tags. For
example:

```
youtube.com video
reddit.com/r/Music music reddit
```

When a bookmark is created or updated, the URL of the bookmark is parsed to extract the hostname, path, and query
string. These components are then compared against the patterns defined in the auto tagging rules. If all components
match, the tags associated with the rule are added to the bookmark. Both the bookmark form in the web interface and the
browser extension will show a preview of the tags that will be added based on the auto tagging rules.

The URL matching works like this:

- **Hostname Matching**: The hostname of the bookmark URL is compared to the hostname in the rule. If the rule does not
  specify a subdomain, it matches all subdomains. For example, a rule with `youtube.com` will match both
  `www.youtube.com` and `m.youtube.com`. If a subdomain is specified in the rule, it will only match that subdomain. For
  example, a rule with `gist.github.com` will only match `gist.github.com`.
- **Path Matching**: The path of the bookmark URL is compared to the path in the rule. If the rule does not specify a
  path, it matches all paths. For example, a rule with `reddit.com` will match `reddit.com/r/music`,
  `reddit.com/r/gaming`, etc. If a path is specified in the rule, it will only match that path and all its subpaths. For
  example, a rule with `reddit.com/r/music` will match `reddit.com/r/music`, `reddit.com/r/music/new`, etc.
- **Query String Matching**: The query string parameters of the bookmark URL are compared to those in the rule. If the
  rule does not specify any query string parameters, it matches all query strings. If the rule specifies a query string
  it will only match if the bookmark URL contains all the specified query string parameters with their respective
  values.

Note that URL matching currently does not support any kind of wildcards. Rule matching only works based on the URL, not
on the content of the website or any other aspect of the bookmark.

## Example

Consider the following auto tagging rule:

```
reddit.com/r/Music music reddit
```

When adding a bookmark for a URL like `https://www.reddit.com/r/Music/comments/...`, the auto tagging mechanism will:

1. Parse the URL to extract the hostname (`www.reddit.com`), path (`/r/Music/comments/...`), and query string (none).
2. Match the hostname against the pattern. The domain `reddit.com` matches. Since the rule does not specify a subdomain,
   it also matches `www.reddit.com`.
3. Match the path against the pattern. The path `/r/Music` also matches the nested path `/r/Music/comments/...`.
4. Match the query string. Since the rule does not specify a query string, it matches all query strings.
5. The tags `music` and `reddit` will be added to the bookmark.
