# How To

Collection of tips and tricks around using linkding.

## Using the bookmarklet on Android/Chrome

This how-to explains the usage of the standard linkding bookmarklet on Android / Chrome. 

Chrome on Android does not permit running bookmarklets in the same way you can on a desktop system. There is however a workaround that is explained here.

**Note** that this only works with Chrome and not with other browsers on Android.

Create a bookmark of your linkding deployment by clicking the star icon which you find in the three dots menu in the top right. Next you have to edit the bookmark. Edit the URL and replace it it with the bookmarklet code of your instance and give it an easy to type name like `bm` for bookmark or `ld` for linkding:

```
javascript: (function() { var bookmarkUrl = window.location; var applicationUrl = 'http://<YOUR_INSTANCE_HERE>/bookmarks/new'; applicationUrl += '?url=' + encodeURIComponent(bookmarkUrl); applicationUrl += '&auto_close'; window.open(applicationUrl);})();
```

Now when you are browsing the web and you want to save the current page as a bookmark to your linkding instance simply type `bm` into the address bar and select it from the results. The bookmarklet code will trigger and you will be redirected so save the current page.

For more info see here: https://paul.kinlan.me/use-bookmarklets-on-chrome-on-android/

