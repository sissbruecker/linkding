---
title: "Troubleshooting"
description: "Common issues and solutions"
---

## Login fails with `403 CSRF verfication failed`

This can be the case when using a reverse proxy that rewrites the `Host` header, such as Nginx.
Since linkding version 1.15, the application includes a CSRF check that verifies that the `Origin` request header matches the `Host` header.
If the `Host` header is modified by the reverse proxy then this check fails.

To fix this, check the [reverse proxy setup documentation](/installation#reverse-proxy-setup) on how to configure header forwarding for your proxy server, or alternatively configure the  [`LD_CSRF_TRUSTED_ORIGINS` option](/options#ld_csrf_trusted_origins) to the URL from which you are accessing your linkding instance.

## Import fails with `502 Bad Gateway`

The default timeout for requests is 60 seconds, after which the application server will cancel the request and return the above error.
Depending on the system that the application runs on, and the number of bookmarks that need to be imported, the import may take longer than the default 60 seconds.

To increase the timeout you can configure the [`LD_REQUEST_TIMEOUT` option](/options#ld_request_timeout).

Note that any proxy servers that you are running in front of linkding may have their own timeout settings, which are not affected by the variable.
