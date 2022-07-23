# Changelog

## v1.12.0 (23/07/2022)

### What's Changed
* Add read it later functionality by @sissbruecker in https://github.com/sissbruecker/linkding/pull/304
* Add RSS feeds by @sissbruecker in https://github.com/sissbruecker/linkding/pull/305
* Add bookmarklet to community by @ukcuddlyguy in https://github.com/sissbruecker/linkding/pull/293
* Shorten and simplify example bookmarklet in documentation by @FunctionDJ in https://github.com/sissbruecker/linkding/pull/297
* Fix typo by @kianmeng in https://github.com/sissbruecker/linkding/pull/295
* Bump django from 3.2.13 to 3.2.14 by @dependabot in https://github.com/sissbruecker/linkding/pull/294
* Bump svelte from 3.46.4 to 3.49.0 by @dependabot in https://github.com/sissbruecker/linkding/pull/299
* Bump terser from 5.5.1 to 5.14.2 by @dependabot in https://github.com/sissbruecker/linkding/pull/302

### New Contributors
* @ukcuddlyguy made their first contribution in https://github.com/sissbruecker/linkding/pull/293
* @FunctionDJ made their first contribution in https://github.com/sissbruecker/linkding/pull/297
* @kianmeng made their first contribution in https://github.com/sissbruecker/linkding/pull/295

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.11.1...v1.12.0

---

## v1.11.1 (03/07/2022)

### What's Changed
* Fix duplicate tags on import by @wahlm in https://github.com/sissbruecker/linkding/pull/289
* Add apple-touch-icon by @daveonkels in https://github.com/sissbruecker/linkding/pull/282
* Bump waybackpy to 3.0.6 by @dustinblackman in https://github.com/sissbruecker/linkding/pull/281

### New Contributors
* @wahlm made their first contribution in https://github.com/sissbruecker/linkding/pull/289
* @daveonkels made their first contribution in https://github.com/sissbruecker/linkding/pull/282
* @dustinblackman made their first contribution in https://github.com/sissbruecker/linkding/pull/281

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.11.0...v1.11.1

---

## v1.11.0 (26/05/2022)

### What's Changed
* Add background tasks to admin by @sissbruecker in https://github.com/sissbruecker/linkding/pull/264
* Improve about section by @sissbruecker in https://github.com/sissbruecker/linkding/pull/265
* Allow creating archived bookmark through REST API by @kencx in https://github.com/sissbruecker/linkding/pull/268
* Add PATCH support to bookmarks endpoint by @sissbruecker in https://github.com/sissbruecker/linkding/pull/269
* Add community reference to linkding-cli by @bachya in https://github.com/sissbruecker/linkding/pull/270

### New Contributors
* @kencx made their first contribution in https://github.com/sissbruecker/linkding/pull/268

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.10.1...v1.11.0

---

## v1.10.1 (21/05/2022)

### What's Changed
* Fake request headers to reduce bot detection by @sissbruecker in https://github.com/sissbruecker/linkding/pull/263


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.10.0...v1.10.1

---

## v1.10.0 (21/05/2022)

### What's Changed
* Add to managed hosting options by @m3nu in https://github.com/sissbruecker/linkding/pull/253
* Add community reference to aiolinkding by @bachya in https://github.com/sissbruecker/linkding/pull/259
* Improve import performance by @sissbruecker in https://github.com/sissbruecker/linkding/pull/261
* Update how-to.md to fix unclear/paraphrased Safari action in IOS Shortcuts by @feoh in https://github.com/sissbruecker/linkding/pull/260
* Allow searching for untagged bookmarks by @sissbruecker in https://github.com/sissbruecker/linkding/pull/226

### New Contributors
* @m3nu made their first contribution in https://github.com/sissbruecker/linkding/pull/253
* @bachya made their first contribution in https://github.com/sissbruecker/linkding/pull/259
* @feoh made their first contribution in https://github.com/sissbruecker/linkding/pull/260

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.9.0...v1.10.0

---

## v1.9.0 (14/05/2022)

### What's Changed
* Scroll menu items into view when using keyboard by @sissbruecker in https://github.com/sissbruecker/linkding/pull/248
* Add whitespace after auto-completed tag by @sissbruecker in https://github.com/sissbruecker/linkding/pull/249
* Bump django from 3.2.12 to 3.2.13 by @dependabot in https://github.com/sissbruecker/linkding/pull/244
* Add community helm chart reference to readme by @pascaliske in https://github.com/sissbruecker/linkding/pull/242
* Feature: Shortcut key for new bookmark by @rithask in https://github.com/sissbruecker/linkding/pull/241
* Clarify archive.org feature by @clach04 in https://github.com/sissbruecker/linkding/pull/229
* Make Internet Archive integration opt-in by @sissbruecker in https://github.com/sissbruecker/linkding/pull/250

### New Contributors
* @pascaliske made their first contribution in https://github.com/sissbruecker/linkding/pull/242
* @rithask made their first contribution in https://github.com/sissbruecker/linkding/pull/241
* @clach04 made their first contribution in https://github.com/sissbruecker/linkding/pull/229

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.8.8...v1.9.0

---

## v1.8.8 (27/03/2022)

- [**bug**] Prevent bookmark actions through get requests
- [**bug**] Prevent external redirects

---

## v1.8.7 (26/03/2022)

- [**bug**] Increase request buffer size [#28](https://github.com/sissbruecker/linkding/issues/28)
- [**enhancement**]  Allow specifying port through LINKDING_PORT environment variable [#156](https://github.com/sissbruecker/linkding/pull/156)
- [**chore**] Bump NPM packages [#224](https://github.com/sissbruecker/linkding/pull/224)

---

## v1.8.6 (25/03/2022)

- [bug] fix bookmark access restrictions
- [bug] prevent external redirects
- [chore] bump dependencies

---

## v1.8.5 (12/12/2021)

- [**bug**] Ensure tag names do not contain spaces [#182](https://github.com/sissbruecker/linkding/issues/182)
- [**bug**] Consider not copying whole GIT repository to Docker image [#174](https://github.com/sissbruecker/linkding/issues/174)
- [**enhancement**] Make bookmarks count column in admin sortable [#183](https://github.com/sissbruecker/linkding/pull/183)

---

## v1.8.4 (16/10/2021)

- [**enhancement**] Allow non-admin users to change their password [#166](https://github.com/sissbruecker/linkding/issues/166)

---

## v1.8.3 (03/10/2021)

- [**enhancement**] Enhancement: let user configure to open links in same tab instead on a new window/tab [#27](https://github.com/sissbruecker/linkding/issues/27)

---

## v1.8.2 (02/10/2021)

- [**bug**] Fix jumping search box [#163](https://github.com/sissbruecker/linkding/pull/163)

---

## v1.8.1 (01/10/2021)

- [**enhancement**] Add global shortcut for search [#161](https://github.com/sissbruecker/linkding/pull/161)
  - allows to press `s` to focus the search input

---

## v1.8.0 (04/09/2021)

- [**enhancement**] Wayback Machine Integration [#59](https://github.com/sissbruecker/linkding/issues/59)
  - Automatically creates snapshots of bookmarked websites on [web archive](https://archive.org/web/)
  - This is one of the largest changes yet and adds a task processor that runs as a separate process in the background. If you run into issues with this feature, it can be disabled using the [LD_DISABLE_BACKGROUND_TASKS](https://github.com/sissbruecker/linkding/blob/master/docs/Options.md#ld_disable_background_tasks) option

---

## v1.7.2 (26/08/2021)

- [**enhancement**] Add support for nanosecond resolution timestamps for bookmark import (e.g. Google Bookmarks) [#146](https://github.com/sissbruecker/linkding/issues/146)

---

## v1.7.1 (25/08/2021)

- [**bug**] umlaut/non-ascii characters broken when using bookmarklet (firefox) [#148](https://github.com/sissbruecker/linkding/issues/148)
- [**bug**] Bookmark import accepts empty URL values [#124](https://github.com/sissbruecker/linkding/issues/124)
- [**enhancement**] Show the version in the settings [#104](https://github.com/sissbruecker/linkding/issues/104)

---

## v1.7.0 (17/08/2021)

- Upgrade to Django 3
- Bump other dependencies

---

## v1.6.5 (15/08/2021)

- [**enhancement**] query with multiple hashtags very slow [#112](https://github.com/sissbruecker/linkding/issues/112)

---

## v1.6.4 (13/05/2021)

- Update dependencies for security fixes

---

## v1.6.3 (06/04/2021)

- [**bug**] relative names use the wrong "today" after day change [#107](https://github.com/sissbruecker/linkding/issues/107)

---

## v1.6.2 (04/04/2021)

- [**enhancement**] Expose `date_added` in UI [#85](https://github.com/sissbruecker/linkding/issues/85)
- [**closed**] Archived bookmarks - no result when searching for a word which is used only as tag [#83](https://github.com/sissbruecker/linkding/issues/83)
- [**closed**] Add archive/unarchive button to edit bookmark page [#82](https://github.com/sissbruecker/linkding/issues/82)
- [**enhancement**] Make scraped title and description editable [#80](https://github.com/sissbruecker/linkding/issues/80)

---

## v1.6.1 (31/03/2021)

- Expose date_added in UI [#85](https://github.com/sissbruecker/linkding/issues/85)

---

## v1.6.0 (28/03/2021)

- Bulk edit mode [#101](https://github.com/sissbruecker/linkding/pull/101)

---

## v1.5.0 (28/03/2021)

- [**closed**] Add a dark mode [#49](https://github.com/sissbruecker/linkding/issues/49)

---

## v1.4.1 (20/03/2021)

- Security patches
- Documentation improvements

---

## v1.4.0 (24/02/2021)

- [**enhancement**] Improve admin utilization [#76](https://github.com/sissbruecker/linkding/issues/76)

---

## v1.3.3 (18/02/2021)

- [**closed**] Missing "description" request body parameter in API causes 500 [#78](https://github.com/sissbruecker/linkding/issues/78)

---

## v1.3.2 (18/02/2021)

- [**closed**] /archive and /unarchive API routes return 404 [#77](https://github.com/sissbruecker/linkding/issues/77)
- [**closed**] API - /api/check_url?url= with token authetification [#55](https://github.com/sissbruecker/linkding/issues/55)

---

## v1.3.1 (15/02/2021)

[enhancement] Enhance delete links with inline confirmation

---

## v1.3.0 (14/02/2021)

- [**closed**] Novice help. [#71](https://github.com/sissbruecker/linkding/issues/71)
- [**closed**] Option to create bookmarks public [#70](https://github.com/sissbruecker/linkding/issues/70)
- [**enhancement**] Show URL if title is not available [#64](https://github.com/sissbruecker/linkding/issues/64)
- [**bug**] minor ui nitpicks [#62](https://github.com/sissbruecker/linkding/issues/62)
- [**enhancement**] add an archive function [#46](https://github.com/sissbruecker/linkding/issues/46)
- [**closed**] remove non fqdn check and alert [#36](https://github.com/sissbruecker/linkding/issues/36)
- [**closed**] Add Lotus Notes links [#22](https://github.com/sissbruecker/linkding/issues/22)

---

## v1.2.1 (12/01/2021)

- [**bug**] Bug: Two equal tags with different capitalisation lead to 500 server errors [#65](https://github.com/sissbruecker/linkding/issues/65)
- [**closed**] Enhancement: category and pagination [#11](https://github.com/sissbruecker/linkding/issues/11)

---

## v1.2.0 (09/01/2021)

- [**closed**] Add Favicon [#58](https://github.com/sissbruecker/linkding/issues/58)
- [**closed**] Make tags case-insensitive [#45](https://github.com/sissbruecker/linkding/issues/45)

---

## v1.1.1 (01/01/2021)

- [**enhancement**] Add docker-compose support [#54](https://github.com/sissbruecker/linkding/pull/54)

---

## v1.1.0 (31/12/2020)

- [**enhancement**] Search autocomplete [#52](https://github.com/sissbruecker/linkding/issues/52)
- [**enhancement**] Improve Netscape bookmarks file parsing [#50](https://github.com/sissbruecker/linkding/issues/50)

---

## v1.0.0 (31/12/2020)

- [**bug**] Import does not import bookmark descriptions [#47](https://github.com/sissbruecker/linkding/issues/47)
- [**enhancement**] Enhancement: return to same page we were on after editing a bookmark [#26](https://github.com/sissbruecker/linkding/issues/26)
- [**bug**] Increase limit on bookmark URL length [#25](https://github.com/sissbruecker/linkding/issues/25)
- [**enhancement**] API for app development [#24](https://github.com/sissbruecker/linkding/issues/24)
- [**enhancement**] Enhancement: detect duplicates at entry time [#23](https://github.com/sissbruecker/linkding/issues/23)
- [**bug**] Error importing bookmarks [#18](https://github.com/sissbruecker/linkding/issues/18)
- [**enhancement**] Enhancement: better administration page [#4](https://github.com/sissbruecker/linkding/issues/4)
- [**enhancement**] Bug: Navigation bar active link stays on add bookmark [#3](https://github.com/sissbruecker/linkding/issues/3)
- [**bug**] CSS Stylesheet presented as text/plain [#2](https://github.com/sissbruecker/linkding/issues/2)