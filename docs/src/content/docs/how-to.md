---
title: "How to"
description: "Collection of tips and tricks around using linkding"
---

Collection of tips and tricks around using linkding.

## Using the bookmarklet on Android/Chrome

This how-to explains the usage of the standard linkding bookmarklet on Android / Chrome. 

Chrome on Android does not permit running bookmarklets in the same way you can on a desktop system. There is however a workaround that is explained here.

**Note** that this only works with Chrome and not with other browsers on Android.

Create a bookmark of your linkding deployment by clicking the star icon which you find in the three dots menu in the top right. Next you have to edit the bookmark. Edit the URL and replace it it with the bookmarklet code of your instance and give it an easy to type name like `bm` for bookmark or `ld` for linkding:

```
javascript:window.open(`http://<YOUR_INSTANCE_HERE>/bookmarks/new?url=${encodeURIComponent(window.location)}&auto_close`)
```

Now when you are browsing the web and you want to save the current page as a bookmark to your linkding instance simply type `bm` into the address bar and select it from the results. The bookmarklet code will trigger and you will be redirected so save the current page.

For more info see here: https://paul.kinlan.me/use-bookmarklets-on-chrome-on-android/

## Using the PWA (Progressive Web App) to save links using the native share sheet on Android

 - Visit your instance in Chrome (works best) or another Chromium-based web browser.
 - A popup should appear (first time only) prompting you to install Linkding as an app. If it doesn't, tap the 3-dot menu then tap "Add to Home screen", then tap "Install".
 - Linkding will now show up in Android's native share sheet. Share a link from any app or browser and tap Linkding to save a link.
 - Optional: when the share sheet is displayed, tap and hold Linkding, then tap "Pin" to pin it to the top.

## Using HTTP Shortcuts app on Android

**Note** This allows you to share URL from any app to tag and bookmark it to linkding

- Install HTTP Shortcuts from [Play Store](https://play.google.com/store/apps/details?id=ch.rmy.android.http_shortcuts) or [F-Droid](https://f-droid.org/en/packages/ch.rmy.android.http_shortcuts/).

- Copy the URL of [linkding_shortcut.json](https://raw.githubusercontent.com/sissbruecker/linkding/master/docs/src/assets/linkding_shortcut.json).

- Open HTTP Shortcuts, tap the 3-dot-button at the top-right corner, tap `Import/Export`, then tap `Import from URL`.

- Paste the URL you copied earlier, tap OK, go back, tap the 3-dot-button again, then tap `Variables`.

- Edit the `values` of `linkding_instance` and `linkding_api_key`.

Try using share button on an app, a new item `Send to...` should appear on the share sheet. You can also manually share by tapping the shortcut inside the HTTP Shortcuts app itself.

## Create a share action on iOS for adding bookmarks to linkding

This how-to explains how to make use of the app shortcuts iOS app to create a share action that can be used in Safari for adding bookmarks to your linkding instance.

To install the shortcut:
- Download the [Shortcut](https://raw.githubusercontent.com/sissbruecker/linkding/master/docs/src/assets/Add%20To%20Linkding.shortcut) on your iOS device
- Tap the downloaded file, which brings up the Shortcuts app
- Confirm that you want to add the shortcut
- In the shortcut, change `https://linkding.mydomain.com` to the URL of your linkding instance
- Confirm / close the shortcut

To use the shortcut:
- Open Safari and navigate to the page you want to bookmark
- Tap the share button
- Scroll down and tap "Add To Linkding"
- This opens linkding in a Safari overlay where you can configure the bookmark
- When you're done, tap "Save"
- After the bookmark is saved you can close the overlay

At the bottom of the share sheet there is a button for configuring share actions. You can use this to move the "Add To Linkding" action to the top of the share sheet if you like.

:::note
You can also check the [Community section](/community) for other pre-made shortcuts that you can use.
:::

## Enable usage tracking for most-used bookmarks

Linkding includes an optional usage tracking feature that helps you find your most frequently accessed bookmarks. This feature is disabled by default and designed with privacy in mind.

### How it works

When enabled, linkding tracks how often you click on bookmark links and provides a "Most Used" sorting option that shows your most frequently accessed bookmarks first. The tracking is:

- **Local only** - Data never leaves your linkding instance
- **Personal** - Only tracks your own clicks, not other users
- **Optional** - Disabled by default, must be explicitly enabled
- **Transparent** - You control when it's active

### Enabling usage tracking

1. Go to **Settings** → **General**
2. Check the **"Enable usage tracking"** option
3. Click **Save**

Once enabled:
- The bookmark sort dropdown will include a new **"Most Used"** option
- Clicking on bookmark links will increment their usage counter
- Most frequently clicked bookmarks will appear first when using "Most Used" sort

### Disabling usage tracking

You can disable usage tracking at any time:

1. Go to **Settings** → **General** 
2. Uncheck the **"Enable usage tracking"** option
3. Click **Save**

When disabled:
- No more click tracking occurs
- The "Most Used" sort option is hidden
- Bookmarks return to date-based sorting only
- Previously collected usage data is preserved but not used

## Increase the font size

The font size can be adjusted globally by adding the following CSS to the custom CSS field in the settings:

```css
:root {
  --font-size: 0.75rem;
  --font-size-sm: 0.7rem;
  --font-size-lg: 0.9rem;
}

.bookmark-list {
  line-height: 1.15rem;
}

.tag-cloud {
  line-height: 1.15rem;
}
```

You can adjust the `--font-size`, `--font-size-sm` and `--font-size-lg` variables to your liking.
Note that increasing the font might also require you to adjust the line-height in certain places to better separate texts from each other.
As an example, the above also increases the font size and line height of the bookmark list and tag cloud.
