# How To

Collection of tips and tricks around using linkding.

## Using the bookmarklet on Android/Chrome

This how-to explains the usage of the standard linkding bookmarklet on Android / Chrome. 

Chrome on Android does not permit running bookmarklets in the same way you can on a desktop system. There is however a workaround that is explained here.

**Note** that this only works with Chrome and not with other browsers on Android.

Create a bookmark of your linkding deployment by clicking the star icon which you find in the three dots menu in the top right. Next you have to edit the bookmark. Edit the URL and replace it it with the bookmarklet code of your instance and give it an easy to type name like `bm` for bookmark or `ld` for linkding:

```
javascript:window.open(`http://m9m.local:9191/bookmarks/new?url=${encodeURIComponent(window.location)}&auto_close`)
```

Now when you are browsing the web and you want to save the current page as a bookmark to your linkding instance simply type `bm` into the address bar and select it from the results. The bookmarklet code will trigger and you will be redirected so save the current page.

For more info see here: https://paul.kinlan.me/use-bookmarklets-on-chrome-on-android/

## Using HTTP Shortcuts app on Android

**Note** This allows you to share URL from any app to bookmark it to linkding

- Install HTTP Shortcuts from [Play Store](https://play.google.com/store/apps/details?id=ch.rmy.android.http_shortcuts) or [F-Droid](https://f-droid.org/en/packages/ch.rmy.android.http_shortcuts/).

- Download [linkding_shortcut.json](/docs/linkding_shortcut.json) from this repository.

- Open HTTP Shortcuts, tap the 3-dot-button at the top-right corner, tap `Import/Export`, then tap `Import from file`.

- Select the json file you downloaded earlier, go back, tap the 3-dot-button again, then tap `Variables`.

- Edit the `values` of `linkding_instance`, `linkding_tag` and `linkding_api_token`.

Try using share button on an app, a new item `Send to...` should appear on the share sheet. You can also manually share by tapping the shortcut inside the HTTP Shortcuts app itself.

## Create a share action on iOS for adding bookmarks to linkding

This how-to explains how to make use of the app shortcuts iOS app to create a share action that can be used in Safari for adding bookmarks to your linkding instance.

**In the shortcuts app:**
- create new shortcut
- go to shortcut details, enable to option to show the shortcut in share menu
- from the available share input types only select "URL"
- add Safari action "Show Web Page At"
- for URL enter your linkding instance URL and specifically point to the new bookmark form, then add the shortcut input variable from the list of suggested variables after the URL parameter. Visually it should look something like this: `https://linkding.mydomain.com/bookmarks/new?url=[Shortcut input]`, where `[Shortcut input]` is a visual block that was inserted after selecting the shortcut input variable suggestion. This is basically a placeholder that will get replaced with the actual URL that you want to bookmark. See screenshot at the end for an example on how this looks.
- save, give the shortcut a nice name + glyph

Example of how the shortcut configuration should look:

![Screenshot](/docs/ios-app-shortcut-example.png?raw=true "Screenshot demonstrating how to insert the input placeholder into the URL")

**Using the share action from Safari:**
- browse to the website that you want to share
- click the share button
- your new app shortcut should now be available as share action
- select the app shortcut
- this should open a new Safari overlay showing the add bookmark form with the URL field prefilled
- after saving the bookmark you can close the overlay and continue browsing

