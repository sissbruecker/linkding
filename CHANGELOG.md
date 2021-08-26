# Changelog

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

## v1.6.3 (07/04/2021)
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

## v1.6.0 (29/03/2021)
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
