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

### `LD_DISABLE_URL_VALIDATION`

Values: `True`, `False` | Default = `False`

Completely disables URL validation for bookmarks. This can be useful if you intend to store non fully qualified domain name URLs, such as network paths, or you want to store URLs that use another protocol than `http` or `https`.

### `LD_REQUEST_TIMEOUT`

Values: `Integer` as seconds | Default = `60`

Configures the request timeout in the uwsgi application server. This can be useful if you want to import a bookmark file with a high number of bookmarks and run into request timeouts.