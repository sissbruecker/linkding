---
title: "Installation"
description: "How to install linkding"
---

linkding is designed to be run with container solutions like [Docker](https://docs.docker.com/get-started/).
The Docker image is compatible with ARM platforms, so it can be run on a Raspberry Pi.

linkding uses an SQLite database by default.
Alternatively, linkding supports PostgreSQL, see the [database options](/options#ld_db_engine) for more information.

##  Using Docker

The Docker image comes in several variants. To use a different image than the default, replace `latest` with the desired tag in the commands below, or in the docker-compose file.

<table>
  <thead>
    <tr>
      <th>Tag</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>latest</code></td>
      <td>Provides the basic functionality of linkding</td>
    </tr>
    <tr>
      <td><code>latest-plus</code></td>
      <td>
        Includes feature for archiving websites as HTML snapshots
        <ul>
          <li>Significantly larger image size as it includes a Chromium installation</li>
          <li>Requires more runtime memory to run Chromium</li>
          <li>Requires more disk space for storing HTML snapshots</li>
        </ul>            
      </td>
    </tr>
    <tr>
      <td><code>latest-alpine</code></td>
      <td><code>latest</code>, but based on Alpine Linux. 🧪 Experimental</td>
    </tr>    
    <tr>
      <td><code>latest-plus-alpine</code></td>
      <td><code>latest-plus</code>, but based on Alpine Linux. 🧪 Experimental</td>
    </tr>    
  </tbody>
</table>

To install linkding using Docker you can just run the image from [Docker Hub](https://hub.docker.com/repository/docker/sissbruecker/linkding):
```shell
docker run --name linkding -p 9090:9090 -v {host-data-folder}:/etc/linkding/data -d sissbruecker/linkding:latest
```

In the command above, replace the `{host-data-folder}` placeholder with an absolute path to a folder on your host system where you want to store the linkding database.

If everything completed successfully, the application should now be running and can be accessed at http://localhost:9090.

To upgrade the installation to a new version, remove the existing container, pull the latest version of the linkding Docker image, and then start a new container using the same command that you used above. There is a [shell script](https://github.com/sissbruecker/linkding/blob/master/install-linkding.sh) available to automate these steps. The script can be configured using environment variables, or you can just modify it.

To complete the setup, you still have to [create an initial user](#user-setup), so that you can access your installation.

##  Using Docker Compose

To install linkding using [Docker Compose](https://docs.docker.com/compose/), you can download the [`docker-compose.yml`](https://github.com/sissbruecker/linkding/blob/master/docker-compose.yml) file. Also download the [`.env.sample`](https://github.com/sissbruecker/linkding/blob/master/.env.sample) file, rename it to `.env`, configure the parameters, and then run:
```shell
docker-compose up -d
```

To complete the setup, you still have to [create an initial user](#user-setup), so that you can access your installation.

## User Setup

The linkding Docker image does not provide an initial user, so you have to create one after setting up an installation. To do so, replace the credentials in the following command and run it:

**Docker**
```shell
docker exec -it linkding python manage.py createsuperuser --username=joe --email=joe@example.com
```

**Docker Compose**
```shell
docker-compose exec linkding python manage.py createsuperuser --username=joe --email=joe@example.com
```

The command will prompt you for a secure password. After the command has completed you can start using the application by logging into the UI with your credentials.

Alternatively, you can automatically create an initial superuser on startup using the [`LD_SUPERUSER_NAME` option](/options#ld_superuser_name).

## Reverse Proxy Setup

When using a reverse proxy, such as Nginx or Apache, you may need to configure your proxy to correctly forward the `Host` header to linkding, otherwise certain requests, such as login, might fail.

<details>
<summary>Apache</summary>

Apache2 does not change the headers by default, and should not
need additional configuration.

An example virtual host that proxies to linkding might look like:
```
<VirtualHost *:9100>
    <Proxy *>
        Order deny,allow
        Allow from all
    </Proxy>

    ProxyPass / http://linkding:9090/
    ProxyPassReverse / http://linkding:9090/
</VirtualHost>
```

For a full example, see the docker-compose configuration in [jhauris/apache2-reverse-proxy](https://github.com/jhauris/linkding/tree/apache2-reverse-proxy)

If you still run into CSRF issues, please check out the [`LD_CSRF_TRUSTED_ORIGINS` option](/options#ld_csrf_trusted_origins).

</details>

<details>
<summary>Caddy 2</summary>

Caddy does not change the headers by default, and should not need any further configuration.

If you still run into CSRF issues, please check out the [`LD_CSRF_TRUSTED_ORIGINS` option](/options#ld_csrf_trusted_origins).

</details>

<details>
<summary>Nginx</summary>

Nginx by default rewrites the `Host` header to whatever URL is used in the `proxy_pass` directive.
To forward the correct headers to linkding, add the following directives to the location block of your Nginx config:
```
location /linkding {
    ...
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

</details>

Instead of configuring header forwarding in your proxy, you can also configure the URL from which you want to access your linkding instance with the  [`LD_CSRF_TRUSTED_ORIGINS` option](/options#ld_csrf_trusted_origins).
