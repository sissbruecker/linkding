<div align="center">
    <br>
    <a href="https://github.com/sissbruecker/linkding">
        <img src="assets/header.svg" height="50">
    </a>
    <br>
</div>

##  Introduction

linkding is a bookmark manager that you can host yourself.
It's designed be to be minimal, fast, and easy to set up using Docker.

The name comes from:
- *link* which is often used as a synonym for URLs and bookmarks in common language
- *Ding* which is German for thing
- ...so basically something for managing your links

**Feature Overview:**
- Clean UI optimized for readability
- Organize bookmarks with tags
- Bulk editing, Markdown notes, read it later functionality
- Share bookmarks with other users or guests
- Automatically provides titles, descriptions and icons of bookmarked websites
- Automatically archive websites, either as local HTML file or on Internet Archive
- Import and export bookmarks in Netscape HTML format
- Installable as a Progressive Web App (PWA)
- Extensions for [Firefox](https://addons.mozilla.org/firefox/addon/linkding-extension/) and [Chrome](https://chrome.google.com/webstore/detail/linkding-extension/beakmhbijpdhipnjhnclmhgjlddhidpe), as well as a bookmarklet
- SSO support via OIDC or authentication proxies
- REST API for developing 3rd party apps
- Admin panel for user self-service and raw data access


**Demo:** https://demo.linkding.link/

**Screenshot:**

![Screenshot](/docs/public/linkding-screenshot.png?raw=true "Screenshot")

## Getting Started

The following links help you to get started with linkding:
- [Install linkding on your own server](https://linkding.link/installation) or [check managed hosting options](https://linkding.link/managed-hosting)
- [Install the browser extension](https://linkding.link/browser-extension)
- [Check out community projects](https://linkding.link/community), which include mobile apps, browser extensions, libraries and more

## Documentation

The full documentation is now available at [linkding.link](https://linkding.link/).

If you want to contribute to the documentation, you can find the source files in the `docs` folder.

If you want to contribute a community project, feel free to [submit a PR](https://github.com/sissbruecker/linkding/edit/master/docs/src/content/docs/community.md).

## Languages and translations

The interface supports English and Simplified Chinese. Use the language selector
on any page to save a preference in this browser. Without an explicit preference,
linkding uses the browser's preferred supported language, falling back to English.
Language choices do not change bookmark URLs, API values, or user content.

Translation coverage includes the web UI, forms, validation messages, dynamic
bookmark/tag counts, relative dates, PWA metadata, and JavaScript interactions.
The browser extension itself is a separate project and is not translated by these
catalogs.

Translations use Django's gettext support. Install GNU gettext (including
`xgettext`, `msgmerge`, and `msgfmt`) alongside the development dependencies.
On Windows, use a Windows gettext distribution and add its `bin` directory to PATH.

To add a language:

1. Register its language code and native name in `LANGUAGES` in
   [bookmarks/settings/base.py](bookmarks/settings/base.py).
2. Run `uv run manage.py makemessages -l <locale> --no-wrap` and
   `uv run manage.py makemessages -d djangojs -l <locale> --no-wrap`.
   For example, Simplified Chinese uses `zh-hans` in `LANGUAGES` but `zh_Hans`
   for the gettext locale directory.
3. Translate both catalogs under `bookmarks/locale/<locale>/LC_MESSAGES/`.
   Keep named placeholders intact, remove reviewed fuzzy markers, and translate
   whole sentences rather than concatenating translated fragments.
4. Run `uv run manage.py compilemessages` before starting the application or tests.
   Generated `.mo` files are ignored by Git; both Docker images compile them during
   the build. No database migration is needed to add a language.
5. Test switching languages, JavaScript messages, fallback to English, and layout.
   Languages with right-to-left scripts may also require layout changes.

For new interface text, use `{% translate %}` / `{% blocktranslate trimmed %}`
in templates, `gettext_lazy` for Python field labels and choices, and `gettext`
(or `ngettext` for counts) for runtime messages. JavaScript uses the Django
JavaScript catalog loaded before the application bundle. Do not translate stored
choice values, API field names, URLs, or user-authored content.

Run `make messages` to refresh the Chinese catalogs and `make compilemessages`
to compile all catalogs. Review newly extracted or fuzzy entries before release.

## Contributing

Small improvements, bugfixes and documentation improvements are always welcome. If you want to contribute a larger feature, consider opening an issue first to discuss it. I may choose to ignore PRs for features that don't align with the project's goals or that I don't want to maintain.

## Development

The application is built using the Django web framework. You can get started by checking out the excellent [Django docs](https://docs.djangoproject.com/en/4.1/). The `bookmarks` folder contains the actual bookmark application. Other than that the code should be self-explanatory / standard Django stuff 🙂.

### Prerequisites
- Python 3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js

### Setup

Initialize the development environment with:
```
make init
```
This sets up a virtual environment using uv, installs NPM dependencies and runs migrations to create the initial database.

Create a user for the frontend:
```
uv run manage.py createsuperuser --username=joe --email=joe@example.com
```

Run the frontend build for bundling frontend components with:
```
make frontend
```

Then start the Django development server with:
```
make serve
```
The frontend is now available under http://localhost:8000

### Tests

Run all tests with pytest:
```
make test
```


### Linting

Run linting with ruff:
```
make lint
```

### Formatting

Format Python code with ruff, Django templates with djlint, and JavaScript code with prettier:
```
make format
```

### DevContainers

This repository also supports DevContainers: [![Open in Remote - Containers](https://img.shields.io/static/v1?label=Remote%20-%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/sissbruecker/linkding.git)

Once checked out, only the following commands are required to get started:

Create a user for the frontend:
```
uv run manage.py createsuperuser --username=joe --email=joe@example.com
```
Start the Node.js development server (used for compiling JavaScript components like tag auto-completion) with:
```
make frontend
```
Start the Django development server with:
```
make serve
```
The frontend is now available under http://localhost:8000
