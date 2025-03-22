---
title: "Troubleshooting"
description: "Common issues and solutions"
---

## Login fails with `403 CSRF verfication failed`

This can be the case when using a reverse proxy that rewrites the `Host` header, such as Nginx.
Since linkding version 1.15, the application includes a CSRF check that verifies that the `Origin` request header matches the `Host` header.
If the `Host` header is modified by the reverse proxy then this check fails.

To fix this, check the [reverse proxy setup documentation](/installation#reverse-proxy-setup) on how to configure header forwarding for your proxy server, or alternatively configure the  [`LD_CSRF_TRUSTED_ORIGINS` option](/options#ld_csrf_trusted_origins) to the URL from which you are accessing your linkding instance.

## Automatically detected title and description are incorrect

linkding automatically fetches the title and description of the web page from the metadata in the HTML `<head>`. This happens on the server, which can return different results than what you see in your browser, for example if a website uses JavaScript to dynamically change the title or description, or if a website requires login.

When using the linkding browser extension, you can enable the *Use browser metadata* option to use the title and description that your browser sees. This will override the server-fetched metadata. Note that for some websites this can give worse results, as not all websites correctly update the metadata in `<head>` while browsing the website (which is why fetching a fresh page on the server is still the default).

The bookmarklet currently does not have such an option.

## Archiving fails for certain websites

When using the server-based archiving feature (available in the `latest-plus` Docker image), you may encounter issues with certain websites where snapshots fail to capture the web page contents correctly.
Common issues include the website showing a bot detection page, a login screen, or some banner that blocks the content.
In rare cases taking a snapshot may also time out.

There are some options to mitigate these issues:
- To capture web page contents exactly as they appear in your browser, use the [Singlefile browser extension](/archiving#using-the-singlefile-browser-extension) or the [linkding browser extension](/archiving#using-the-linkding-browser-extension) with Singlefile integration.
- You can pass custom options to the SingleFile CLI, which linkding uses to capture web pages on the server, using the [`LD_SINGLEFILE_OPTIONS`](/options#ld_singlefile_options) environment variable. For example, changing the user agent might help with some bot detection systems.
- If snapshots are timing out, you can increase the timeout by setting the [`LD_SINGLEFILE_TIMEOUT_SEC`](/options#ld_singlefile_timeout_sec) environment variable to a higher value.

Check the [archiving documentation](/archiving) for more information on how to archive web pages with linkding.

## URL validation fails for seemingly valid URLs

When adding a bookmark, you may encounter URL validation errors even for URLs that seem valid and work in your browser. This is because linkding uses Django's URL validator, which has some limitations in what it considers a valid URL.

Common cases that may fail validation:
- Domains that contain an underscore
- URLs without a top-level domain
- URLs with a non-standard protocol (e.g. `chrome://`)

If you need to store URLs that don't pass the default validation, you can disable URL validation completely by setting the `LD_DISABLE_URL_VALIDATION` option to `True`. See the [options documentation](/options#ld_disable_url_validation) for how to configure this setting.

Further info:
- https://github.com/sissbruecker/linkding/issues/206
- https://code.djangoproject.com/ticket/18517
