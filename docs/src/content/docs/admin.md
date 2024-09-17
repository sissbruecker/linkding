---
title: "Admin"
description: "How to use the linkding admin app"
---

This document describes how to make use of the admin app that comes as part of each linkding installation. This is the default Django admin app with some linkding specific customizations.

The admin app provides several features that are not available in the linkding UI:
- User management and user self-management
- Bookmark and tag management, including bulk operations

## Linkding administration page

To open the Admin app, go the *Settings* view and click on the *Admin* tab. This should open a new window with the admin app.

Alternatively you can open the URL directly by adding `/admin` to the URL of your linkding installation.

## User management

Go to the linkding administration page and select *Users*.
Here you can add and delete users, and change the password of a user.

Once you have added a user you can, if needed, give the user staff status, which means this user can also access the linkding administration page.

This page also allows you to change your own password if necessary.

## Bookmark management

While the linkding UI itself now has a bulk edit feature for bookmarks you can also use the admin app to manage bookmarks or to do bulk operations. 

In the main linkding administration page, choose *Bookmarks*.

First select the bookmarks to operate on:

- Specify a filter to determine which bookmarks to operate on:
  - In the column *by username*, you can choose to filter for bookmarks for a specific user
  - In the column *by is archived*, you can choose to filter for bookmarks that are either archived or not
  - In the column *by tags*, you can choose to filter for specific tags
  - In the search box you can also add a text filter (note that this doesn't use the same search syntax as the linkding UI itself)  

Now a list of bookmarks which match your filter is displayed, each bookmark on a separate line.
Each line starts with a checkbox.
Either choose the individual bookmarks you want to do a bulk operation on, or choose the top checkbox to select all shown bookmarks.

Open the "Action" select box to choose the desired bulk operation:

- Delete
- Archive
- Unarchive

Click the button next to the checkbox to execute the operation.

## Tag management

While linkding UI currently only allows to create or assign tags, you can use the admin app to manage your tags. This can be especially useful if you want to clean up your tag collection.

In the main linkding administration page, choose *Tags*.

Similar to bookmarks management described above you can now specify which tags to operate on by specifying a filter and then selecting the individual tags.

Open the "Action" select box to choose the desired bulk operation:

- Delete
- Delete unused tags - this will only delete the selected tags that are currently not assigned to any bookmark

Click the button next to the checkbox to execute the operation.

Note that deleting a tag does not affect the bookmarks that are tagged with this tag, it only removes the tag from those bookmarks.
