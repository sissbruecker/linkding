---
title: "Archiving"
description: "How to archive web pages with linkding"
---

Linkding allows to archive bookmarked web pages as HTML files. This can be useful to preserve the content of a web page in case it goes offline or its content changes. The sections below explain different methods to archive web pages and store them in linkding.

## Server-based Archiving

Linkding can automatically create HTML snapshots whenever a bookmark is added. This feature is only available in the `latest-plus` Docker image (see [Installation](/installation#using-docker)), and is automatically active when using that image.

The snapshots are created using [singlefile-cli](https://github.com/gildas-lormeau/single-file-cli), which effectively runs a headless Chromium instance on the server to convert the web page into a single HTML file. Linkding will also load the [uBlock Origin Lite extension](https://github.com/uBlockOrigin/uBOL-home) into Chromium to attempt to block ads and other unwanted content.

This method is fairly easy to set up, but also has several downsides:
- The Docker image is significantly larger than the base image, as it includes a Chromium installation.
- Running Chromium requires significantly more memory, at least 1 GB of RAM.
- The Docker image is not available for ARM v7 platforms.
- Creating snapshots from a headless browser is not always reliable, for example:
  - It may trigger anti-bot measures on the website.
  - Websites that require login will not show the same content you would see in your browser.

Read on for alternative methods to archive web pages directly from your browser, which do not require the `latest-plus` Docker image and will save the web page exactly as you see it in your browser.

## Using the Singlefile Browser Extension

[Singlefile](https://github.com/gildas-lormeau/SingleFile) is a popular browser extension for saving a web page as a single HTML file. By default, the extension saves the file to your local disk, but it can also be configured to send the file to a REST API endpoint. Linkding provides a REST API endpoint for this purpose.

To use the Singlefile extension with linkding, follow these steps:
- Install the [Singlefile extension](https://github.com/gildas-lormeau/SingleFile) in your browser
- Open the extension's settings
- Under `Destination`, select `upload to a REST Form API`
- Under `URL` enter the URL of your linkding installation, followed by `/api/bookmarks/singlefile/` (e.g. `https://linkding.example.com/api/bookmarks/singlefile/`)
- Under `authorization token`, enter the REST API token that you can get from your linkding settings page
- Under `data field name` enter `file`
- Under `URL field name` enter `url`

Now, when you click the Singlefile extension icon, the web page will be saved as a single HTML file and uploaded to your linkding installation.
Note that if a bookmark for that URL does not exist, linkding will automatically create a new bookmark. If a bookmark already exists, the snapshot will be added to the existing bookmark.

Using this method has some downsides, in that you can not provide any additional metadata to the bookmark, such as tags or a description. Read on for how to use the linkding extension directly to create bookmarks with metadata and run the Singlefile extension.

## Using the linkding Browser Extension

The linkding extension allows you to quickly add bookmarks from your browser. It can also integrate with the Singlefile extension to automatically create a snapshot of the web page when adding a bookmark.

To integrate with the Singlefile extension, follow these steps:
- First, install and configure the Singlefile extension as described above so that it uploads files to your linkding installation
- Open the linkding extension settings
- Enable the `Run Singlefile after adding new bookmark` option
- Save the settings

Now, when you add a bookmark through the linkding extension, it will automatically trigger the Singlefile extension to create a snapshot of the web page, which will then be uploaded to your linkding installation and stored under the newly added bookmark.

Note that when the option is enabled, linkding will not attempt to create an HTML snapshot on the server, even if you are using the `latest-plus` Docker image. The linkding extension will not trigger Singlefile when updating an existing bookmark. If you want to create a new snapshot for an existing bookmark, you can do so manually by clicking the Singlefile extension icon.
