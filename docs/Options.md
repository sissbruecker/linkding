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