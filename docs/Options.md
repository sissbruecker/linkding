# Options

This document lists the options that linkding can be configured with and explains how to use them in the individual install scenarios.

## Using options

### Docker

Options are passed as environment variables to the Docker container by using the `-e` argument when using `docker run`. For example:

```
docker run --name linkding -p 9090:9090 -d -e LD_DISABLE_URL_VALIDATION=True sissbruecker/linkding:latest
```

For multiple options, use one `-e` argument per option.

### Docker-compose

For docker-compose options are configured using an `.env` file. 
Follow the docker-compose setup in the README and copy `.env.sample` to `.env`. Then modify the options in `.env`.

### Manual setup

All options need to be defined as environment variables in the environment that linkding runs in.

## List of options

### `LD_SUPERUSER_NAME`

Values: `String` | Default = None

When set, creates an initial superuser with the specified username when starting the container.
Does nothing if the user already exists.

See [`LD_SUPERUSER_PASSWORD`](#ld_superuser_password) on how to configure the respective password.

### `LD_SUPERUSER_PASSWORD`

Values: `String` | Default = None

The password for the initial superuser.
When left undefined, the superuser will be created without a usable password, which means the user can not authenticate using credentials / through the login form, and can only be authenticated using proxy authentication (see [`LD_ENABLE_AUTH_PROXY`](#ld_enable_auth_proxy)).

### `LD_DISABLE_BACKGROUND_TASKS`

Values: `True`, `False` | Default = `False`

Disables background tasks, such as creating snapshots for bookmarks on the [the Internet Archive Wayback Machine](https://archive.org/web/).
Enabling this flag will prevent the background task processor from starting up, and prevents scheduling tasks.
This might be useful if you are experiencing performance issues or other problematic behaviour due to background task processing.

### `LD_DISABLE_URL_VALIDATION`

Values: `True`, `False` | Default = `False`

Completely disables URL validation for bookmarks.
This can be useful if you intend to store non fully qualified domain name URLs, such as network paths, or you want to store URLs that use another protocol than `http` or `https`.

### `LD_REQUEST_TIMEOUT`

Values: `Integer` as seconds | Default = `60`

Configures the request timeout in the uwsgi application server. This can be useful if you want to import a bookmark file with a high number of bookmarks and run into request timeouts.

### `LD_SERVER_PORT`

Values: Valid port number | Default = `9090`

Allows to set a custom port for the UWSGI server running in the container. While Docker containers have their own IP address namespace and port collisions are impossible to achieve, there are other container solutions that share one. Podman, for example, runs all containers in a pod under one namespace, which results in every port only being allowed to be assigned once. This option allows to set a custom port in order to avoid collisions with other containers.

### `LD_CONTEXT_PATH`

Values: `String` | Default = None

Allows configuring the context path of the website. Useful for setting up Nginx reverse proxy.
The context path must end with a slash. For example: `linkding/`

### `LD_ENABLE_AUTH_PROXY`

Values: `True`, `False` | Default = `False`

Enables support for authentication proxies such as Authelia.
This effectively disables credentials-based authentication and instead authenticates users if a specific request header contains a known username.
You must make sure that your proxy (nginx, Traefik, Caddy, ...) forwards this header from your auth proxy to linkding. Check the documentation of your auth proxy and your reverse proxy on how to correctly set this up.

Note that this automatically creates new users in the database if they do not already exist.

Enabling this setting also requires configuring the following options:
- `LD_AUTH_PROXY_USERNAME_HEADER` - The name of the request header that the auth proxy passes to the proxied application (linkding in this case), so that the application can identify the user.
Check the documentation of your auth proxy to get this information.
Note that the request headers are rewritten in linkding: all HTTP headers are prefixed with `HTTP_`, all letters are in uppercase, and dashes are replaced with underscores.
For example, for Authelia, which passes the `Remote-User` HTTP header, the `LD_AUTH_PROXY_USERNAME_HEADER` needs to be configured as `HTTP_REMOTE_USER`.
- `LD_AUTH_PROXY_LOGOUT_URL` - The URL that linkding should redirect to after a logout.
By default, the logout redirects to the login URL, which means the user will be automatically authenticated again.
Instead, you might want to configure the logout URL of the auth proxy here.

### `LD_ENABLE_OIDC`

Values: `True`, `False` | Default = `False`

Enables support for OpenID Connect (OIDC) authentication, allowing to use single sign-on (SSO) with OIDC providers.
When enabled, this shows a button on the login page that allows users to authenticate using an OIDC provider.
Users are associated by the email address provided from the OIDC provider, which is used as the username in linkding.
If there is no user with that email address as username, a new user is created automatically. 

This requires configuring a number of options, which of those you need depends on which OIDC provider you use and how it is configured.
In general, you should find the required information in the UI of your OIDC provider, or its documentation. 

The options are adopted from the [mozilla-django-oidc](https://mozilla-django-oidc.readthedocs.io/en/stable/) library, which is used by linkding for OIDC support.
Please check their documentation for more information on the options.

The following options can be configured:
- `OIDC_OP_AUTHORIZATION_ENDPOINT` - The authorization endpoint of the OIDC provider.
- `OIDC_OP_TOKEN_ENDPOINT` - The token endpoint of the OIDC provider.
- `OIDC_OP_USER_ENDPOINT` - The user info endpoint of the OIDC provider.
- `OIDC_OP_JWKS_ENDPOINT` - The JWKS endpoint of the OIDC provider.
- `OIDC_RP_CLIENT_ID` - The client ID of the application.
- `OIDC_RP_CLIENT_SECRET` - The client secret of the application.
- `OIDC_RP_SIGN_ALGO` - The algorithm the OIDC provider uses to sign ID tokens. Default is `RS256`.
- `OIDC_USE_PKCE` - Whether to use PKCE for the OIDC flow. Default is `True`.

### `LD_CSRF_TRUSTED_ORIGINS`

Values: `String` | Default = None

List of trusted origins / host names to allow for `POST` requests, for example when logging in, or saving bookmarks.
For these type of requests, the `Origin` header must match the `Host` header, otherwise the request will fail with a `403` status code, and the message `CSRF verification failed.`

This option allows to declare a list of trusted origins that will be accepted even if the headers do not match. This can be the case when using a reverse proxy that rewrites the `Host` header, such as Nginx.

For example, to allow requests to https://linkding.mydomain.com, configure the setting to `https://linkding.mydomain.com`.
Note that the setting **must** include the correct protocol (`https` or `http`), and **must not** include the application / context path.
Multiple origins can be specified by separating them with a comma (`,`).

This setting is adopted from the Django framework used by linkding, more information on the setting is available in the [Django documentation](https://docs.djangoproject.com/en/4.0/ref/settings/#std-setting-CSRF_TRUSTED_ORIGINS).

### `LD_LOG_X_FORWARDED_FOR`

Values: `true` or `false` | Default =  `false`

Set uWSGI [log-x-forwarded-for](https://uwsgi-docs.readthedocs.io/en/latest/Options.html?#log-x-forwarded-for) parameter allowing to keep the real IP of clients in logs when using a reverse proxy.

### `LD_DB_ENGINE`

Values: `postgres` or `sqlite` | Default = `sqlite`

Database engine used by linkding to store data.
Currently, linkding supports SQLite and PostgreSQL.
By default, linkding uses SQLite, for which you don't need to configure anything.
All the other database variables below are only required for configured PostgresSQL.

### `LD_DB_DATABASE`

Values: `String` | Default =  `linkding`

The name of the database. 

### `LD_DB_USER`

Values: `String` | Default =  `linkding`

The name of the user to connect to the database server.

### `LD_DB_PASSWORD`

Values: `String` | Default =  None

The password of the user to connect to the database server.
The password must be configured when using a database other than SQLite, there is no default value.

### `LD_DB_HOST`

Values: `String` | Default =  `localhost`

The hostname or IP of the database server.

### `LD_DB_PORT`

Values: `Integer` | Default =  None

The port of the database server.
Should use the default port if left empty, for example `5432` for PostgresSQL.

### `LD_DB_OPTIONS`

Values: `String` | Default = `{}`

A json string with additional options for the database. Passed directly to OPTIONS.

### `LD_FAVICON_PROVIDER`

Values: `String` | Default =  `https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={url}&size=32`

The favicon provider used for downloading icons if they are enabled in the user profile settings.
The default provider is a Google service that automatically detects the correct favicon for a website, and provides icons in consistent image format (PNG) and in a consistent image size.

This setting allows to configure a custom provider in form of a URL.
When calling the provider with the URL of a website, it must return the image data for the favicon of that website.
The configured favicon provider URL must contain a placeholder that will be replaced with the URL of the website for which to download the favicon.
The available placeholders are:
- `{url}` - Includes the scheme and hostname of the website, for example `https://example.com`
- `{domain}` - Includes only the hostname of the website, for example `example.com`

Which placeholder you need to use depends on the respective favicon provider, please check their documentation or usage examples.
See the default URL for how to insert the placeholder to the favicon provider URL.

Alternative favicon providers:
- DuckDuckGo: `https://icons.duckduckgo.com/ip3/{domain}.ico`
