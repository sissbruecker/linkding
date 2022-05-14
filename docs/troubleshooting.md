# Troubleshooting

## Import fails with `502 Bad Gateway`

The default timeout for requests is 60 seconds, after which the application server will cancel the request and return the above error.
Depending on the system that the application runs on, and the number of bookmarks that need to be imported, the import may take longer than the default 60 seconds.

To increase the timeout you can configure the [`LD_REQUEST_TIMEOUT` option](Options.md#LD_REQUEST_TIMEOUT).

Note that any proxy servers that you are running in front of linkding may have their own timeout settings, which are not affected by the variable.
