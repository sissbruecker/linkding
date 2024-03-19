# Changelog

## v1.25.0 (18/03/2024)

### What's Changed
* Improve PWA capabilities by @hugo-vrijswijk in https://github.com/sissbruecker/linkding/pull/630
* build improvements by @hugo-vrijswijk in https://github.com/sissbruecker/linkding/pull/649
* Add support for oidc by @Nighmared in https://github.com/sissbruecker/linkding/pull/389
* Add option for custom CSS by @sissbruecker in https://github.com/sissbruecker/linkding/pull/652
* Update backup location to safe directory by @bphenriques in https://github.com/sissbruecker/linkding/pull/653
* Include web archive link in /api/bookmarks/ by @sissbruecker in https://github.com/sissbruecker/linkding/pull/655
* Add RSS feeds for shared bookmarks by @sissbruecker in https://github.com/sissbruecker/linkding/pull/656
* Bump django from 5.0.2 to 5.0.3 by @dependabot in https://github.com/sissbruecker/linkding/pull/658

### New Contributors
* @hugo-vrijswijk made their first contribution in https://github.com/sissbruecker/linkding/pull/630
* @Nighmared made their first contribution in https://github.com/sissbruecker/linkding/pull/389
* @bphenriques made their first contribution in https://github.com/sissbruecker/linkding/pull/653

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.24.2...v1.25.0

---

## v1.24.2 (16/03/2024)

### What's Changed
* Fix logout button by @sissbruecker in https://github.com/sissbruecker/linkding/pull/648


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.24.1...v1.24.2

---

## v1.24.1 (16/03/2024)

### What's Changed
* Bump dependencies by @sissbruecker in https://github.com/sissbruecker/linkding/pull/618
* Persist secret key in data folder by @sissbruecker in https://github.com/sissbruecker/linkding/pull/620
* Group ideographic characters in tag cloud by @jonathan-s in https://github.com/sissbruecker/linkding/pull/613
* Bump django from 5.0.1 to 5.0.2 by @dependabot in https://github.com/sissbruecker/linkding/pull/625
* Add k8s setup to community section by @jzck in https://github.com/sissbruecker/linkding/pull/633
* Added a new Linkding client to community section by @JGeek00 in https://github.com/sissbruecker/linkding/pull/638

### New Contributors
* @jzck made their first contribution in https://github.com/sissbruecker/linkding/pull/633
* @JGeek00 made their first contribution in https://github.com/sissbruecker/linkding/pull/638

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.24.0...v1.24.1

---

## v1.24.0 (27/01/2024)

### What's Changed
* Support Open Graph description by @jonathan-s in https://github.com/sissbruecker/linkding/pull/602
* Add tooltip to truncated bookmark titles by @jonathan-s in https://github.com/sissbruecker/linkding/pull/607
* Improve bulk tag performance by @sissbruecker in https://github.com/sissbruecker/linkding/pull/612
* Increase tag limit in tag autocomplete by @hypebeast in https://github.com/sissbruecker/linkding/pull/581
* Add CapRover as managed hosting option by @adamshand in https://github.com/sissbruecker/linkding/pull/585
* Bump playwright dependencies by @jonathan-s in https://github.com/sissbruecker/linkding/pull/601
* Adjust archive.org donation link in general.html by @JnsDornbusch in https://github.com/sissbruecker/linkding/pull/603

### New Contributors
* @hypebeast made their first contribution in https://github.com/sissbruecker/linkding/pull/581
* @adamshand made their first contribution in https://github.com/sissbruecker/linkding/pull/585
* @jonathan-s made their first contribution in https://github.com/sissbruecker/linkding/pull/601
* @JnsDornbusch made their first contribution in https://github.com/sissbruecker/linkding/pull/603

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.23.1...v1.24.0

---

## v1.23.1 (08/12/2023)

### What's Changed
* Properly encode search query param by @sissbruecker in https://github.com/sissbruecker/linkding/pull/587

> [!WARNING] 
> *This resolves a security vulnerability in linkding. Everyone is encouraged to upgrade to the latest version as soon as possible.*

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.23.0...v1.23.1

---

## v1.23.0 (24/11/2023)

### What's Changed
* Add Alpine based Docker image (experimental) by @sissbruecker in https://github.com/sissbruecker/linkding/pull/570
* Add backup CLI command by @sissbruecker in https://github.com/sissbruecker/linkding/pull/571
* Update browser extension links by @OPerepadia in https://github.com/sissbruecker/linkding/pull/574
* Include archived bookmarks in export by @sissbruecker in https://github.com/sissbruecker/linkding/pull/579

### New Contributors
* @OPerepadia made their first contribution in https://github.com/sissbruecker/linkding/pull/574

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.22.3...v1.23.0

---

## v1.22.3 (04/11/2023)

### What's Changed
* Fix RSS feed not handling None values  by @vitormarcal in https://github.com/sissbruecker/linkding/pull/569
* Bump django from 4.1.10 to 4.1.13 by @dependabot in https://github.com/sissbruecker/linkding/pull/567

### New Contributors
* @vitormarcal made their first contribution in https://github.com/sissbruecker/linkding/pull/569

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.22.2...v1.22.3

---

## v1.22.2 (27/10/2023)

### What's Changed
* Fix search options not opening on iOS by @sissbruecker in https://github.com/sissbruecker/linkding/pull/549
* Bump urllib3 from 1.26.11 to 1.26.17 by @dependabot in https://github.com/sissbruecker/linkding/pull/542
* Add iOS shortcut to community section by @andrewdolphin in https://github.com/sissbruecker/linkding/pull/550
* Disable editing of search preferences in user admin by @sissbruecker in https://github.com/sissbruecker/linkding/pull/555
* Add feed2linkding to community section by @Strubbl in https://github.com/sissbruecker/linkding/pull/544
* Sanitize RSS feed to remove control characters by @sissbruecker in https://github.com/sissbruecker/linkding/pull/565
* Bump urllib3 from 1.26.17 to 1.26.18 by @dependabot in https://github.com/sissbruecker/linkding/pull/560

### New Contributors
* @andrewdolphin made their first contribution in https://github.com/sissbruecker/linkding/pull/550
* @Strubbl made their first contribution in https://github.com/sissbruecker/linkding/pull/544

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.22.1...v1.22.2

---

## v1.22.1 (06/10/2023)

### What's Changed
* Fix memory leak with SQLite by @sissbruecker in https://github.com/sissbruecker/linkding/pull/548


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.22.0...v1.22.1

---

## v1.22.0 (01/10/2023)

### What's Changed
* Fix case-insensitive search for unicode characters in SQLite by @sissbruecker in https://github.com/sissbruecker/linkding/pull/520
* Add sort option to bookmark list by @sissbruecker in https://github.com/sissbruecker/linkding/pull/522
* Add button to show tags on smaller screens by @sissbruecker in https://github.com/sissbruecker/linkding/pull/529
* Make code blocks in notes scrollable by @sissbruecker in https://github.com/sissbruecker/linkding/pull/530
* Add filter for shared state by @sissbruecker in https://github.com/sissbruecker/linkding/pull/531
* Add support for exporting/importing bookmark notes by @sissbruecker in https://github.com/sissbruecker/linkding/pull/532
* Add filter for unread state by @sissbruecker in https://github.com/sissbruecker/linkding/pull/535
* Allow saving search preferences by @sissbruecker in https://github.com/sissbruecker/linkding/pull/540
* Add user profile endpoint by @sissbruecker in https://github.com/sissbruecker/linkding/pull/541


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.21.0...v1.22.0

---

## v1.21.1 (26/09/2023)

### What's Changed
* Fix bulk edit to respect searched tags by @sissbruecker in https://github.com/sissbruecker/linkding/pull/537


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.21.0...v1.21.1

---

## v1.21.0 (25/08/2023)

### What's Changed
* Make search autocomplete respect link target setting by @sissbruecker in https://github.com/sissbruecker/linkding/pull/513
* Various CSS improvements by @sissbruecker in https://github.com/sissbruecker/linkding/pull/514
* Display shared state in bookmark list by @sissbruecker in https://github.com/sissbruecker/linkding/pull/515
* Allow bulk editing unread and shared state of bookmarks by @sissbruecker in https://github.com/sissbruecker/linkding/pull/517
* Bump uwsgi from 2.0.20 to 2.0.22 by @dependabot in https://github.com/sissbruecker/linkding/pull/516


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.20.1...v1.21.0

---

## v1.20.1 (23/08/2023)

### What's Changed
* Update cached styles and scripts after version change by @sissbruecker in https://github.com/sissbruecker/linkding/pull/510


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.20.0...v1.20.1

---

## v1.20.0 (22/08/2023)

### What's Changed
* Add option to share bookmarks publicly by @sissbruecker in https://github.com/sissbruecker/linkding/pull/503
* Various improvements to favicons by @sissbruecker in https://github.com/sissbruecker/linkding/pull/504
* Add support for PRIVATE flag in import and export by @sissbruecker in https://github.com/sissbruecker/linkding/pull/505
* Avoid page reload when triggering actions in bookmark list by @sissbruecker in https://github.com/sissbruecker/linkding/pull/506


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.19.1...v1.20.0

---

## v1.19.1 (29/07/2023)

### What's Changed
* Add Postman Collection to Community section of README by @gingerbeardman in https://github.com/sissbruecker/linkding/pull/476
* Added Dev Container support by @acbgbca in https://github.com/sissbruecker/linkding/pull/474
* Added Apple web-app meta tag #358 by @acbgbca in https://github.com/sissbruecker/linkding/pull/359
* Bump requests from 2.28.1 to 2.31.0 by @dependabot in https://github.com/sissbruecker/linkding/pull/478
* Allow passing title and description to new bookmark form by @acbgbca in https://github.com/sissbruecker/linkding/pull/479
* Enable WAL to avoid locked database lock errors by @sissbruecker in https://github.com/sissbruecker/linkding/pull/480
* Fix website loader content encoding detection by @sissbruecker in https://github.com/sissbruecker/linkding/pull/482
* Bump certifi from 2022.12.7 to 2023.7.22 by @dependabot in https://github.com/sissbruecker/linkding/pull/497
* Bump django from 4.1.9 to 4.1.10 by @dependabot in https://github.com/sissbruecker/linkding/pull/494

### New Contributors
* @gingerbeardman made their first contribution in https://github.com/sissbruecker/linkding/pull/476
* @acbgbca made their first contribution in https://github.com/sissbruecker/linkding/pull/474

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.19.0...v1.19.1

---

## v1.19.0 (20/05/2023)

### What's Changed
* Add notes to bookmarks by @sissbruecker in https://github.com/sissbruecker/linkding/pull/472


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.18.0...v1.19.0

---

## v1.18.0 (18/05/2023)

### What's Changed
* Make search case-insensitive on Postgres by @sissbruecker in https://github.com/sissbruecker/linkding/pull/432
* Allow searching for tags without hash character by @sissbruecker in https://github.com/sissbruecker/linkding/pull/449
* Prevent zoom-in after focusing an input on small viewports on iOS devices by @puresick in https://github.com/sissbruecker/linkding/pull/440
* Add database options by @plockaby in https://github.com/sissbruecker/linkding/pull/406
* Allow to log real client ip in logs when using a reverse proxy by @fmenabe in https://github.com/sissbruecker/linkding/pull/398
* Add option to display URL below title by @bah0 in https://github.com/sissbruecker/linkding/pull/365
* Add LinkThing iOS app to community section by @amoscardino in https://github.com/sissbruecker/linkding/pull/446
* Bump django from 4.1.7 to 4.1.9 by @dependabot in https://github.com/sissbruecker/linkding/pull/466
* Bump sqlparse from 0.4.2 to 0.4.4 by @dependabot in https://github.com/sissbruecker/linkding/pull/455

### New Contributors
* @amoscardino made their first contribution in https://github.com/sissbruecker/linkding/pull/446
* @puresick made their first contribution in https://github.com/sissbruecker/linkding/pull/440
* @plockaby made their first contribution in https://github.com/sissbruecker/linkding/pull/406
* @fmenabe made their first contribution in https://github.com/sissbruecker/linkding/pull/398
* @bah0 made their first contribution in https://github.com/sissbruecker/linkding/pull/365

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.17.2...v1.18.0

---

## v1.17.2 (18/02/2023)

### What's Changed
* Escape texts in exported HTML by @sissbruecker in https://github.com/sissbruecker/linkding/pull/429
* Bump django from 4.1.2 to 4.1.7 by @dependabot in https://github.com/sissbruecker/linkding/pull/427
* Make health check in Dockerfile honor context path setting by @mrex in https://github.com/sissbruecker/linkding/pull/407
* Disable autocapitalization for tag input form by @joshdick in https://github.com/sissbruecker/linkding/pull/395

### New Contributors
* @mrex made their first contribution in https://github.com/sissbruecker/linkding/pull/407
* @joshdick made their first contribution in https://github.com/sissbruecker/linkding/pull/395

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.17.1...v1.17.2

---

## v1.17.1 (22/01/2023)

### What's Changed
* Fix favicon being cleared by web archive snapshot task by @sissbruecker in https://github.com/sissbruecker/linkding/pull/405


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.17.0...v1.17.1

---

## v1.17.0 (21/01/2023)

### What's Changed
* Add Health Check endpoint  by @mckennajones in https://github.com/sissbruecker/linkding/pull/392
* Cache website metadata to avoid duplicate scraping by @sissbruecker in https://github.com/sissbruecker/linkding/pull/401
* Prefill form if URL is already bookmarked by @sissbruecker in https://github.com/sissbruecker/linkding/pull/402
* Add option for showing bookmark favicons by @sissbruecker in https://github.com/sissbruecker/linkding/pull/390


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.16.1...v1.17.0

---

## v1.16.1 (20/01/2023)

### What's Changed
* Fix bookmark website metadata not being updated when URL changes by @sissbruecker in https://github.com/sissbruecker/linkding/pull/400
* Bump django from 4.1 to 4.1.2 by @dependabot in https://github.com/sissbruecker/linkding/pull/391
* Bump certifi from 2022.6.15 to 2022.12.7 by @dependabot in https://github.com/sissbruecker/linkding/pull/374
* Bump minimatch from 3.0.4 to 3.1.2 by @dependabot in https://github.com/sissbruecker/linkding/pull/366


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.16.0...v1.16.1

---

## v1.16.0 (12/01/2023)

### What's Changed
* Add postgres as database engine by @tomamplius in https://github.com/sissbruecker/linkding/pull/388
* Gracefully stop docker container when it receives SIGTERM by @mckennajones in https://github.com/sissbruecker/linkding/pull/368
* Limit document size for website scraper by @sissbruecker in https://github.com/sissbruecker/linkding/pull/354
* Add error handling for checking latest version by @sissbruecker in https://github.com/sissbruecker/linkding/pull/360
* Trim website metadata title and description by @luca1197 in https://github.com/sissbruecker/linkding/pull/383
* Only show admin link for superusers by @AlexanderS in https://github.com/sissbruecker/linkding/pull/384
* Add apache reverse proxy documentation. by @jhauris in https://github.com/sissbruecker/linkding/pull/371
* Correct LD_ENABLE_AUTH_PROXY documentation by @jhauris in https://github.com/sissbruecker/linkding/pull/379
* Android HTTP shortcuts v3 by @kzshantonu in https://github.com/sissbruecker/linkding/pull/387

### New Contributors
* @jhauris made their first contribution in https://github.com/sissbruecker/linkding/pull/371
* @AlexanderS made their first contribution in https://github.com/sissbruecker/linkding/pull/384
* @mckennajones made their first contribution in https://github.com/sissbruecker/linkding/pull/368
* @tomamplius made their first contribution in https://github.com/sissbruecker/linkding/pull/388
* @luca1197 made their first contribution in https://github.com/sissbruecker/linkding/pull/383

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.15.1...v1.16.0

---

## v1.15.1 (05/10/2022)

### What's Changed
* Fix static file dir warning by @sissbruecker in https://github.com/sissbruecker/linkding/pull/350
* Add setting and documentation for fixing CSRF errors by @sissbruecker in https://github.com/sissbruecker/linkding/pull/349


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.15.0...v1.15.1

---

## v1.15.0 (11/09/2022)

### What's Changed
* Bump Django and other dependencies by @sissbruecker in https://github.com/sissbruecker/linkding/pull/331
* Add option to create initial superuser by @sissbruecker in https://github.com/sissbruecker/linkding/pull/323
* Improved Android HTTP Shortcuts doc by @kzshantonu in https://github.com/sissbruecker/linkding/pull/330
* Minify bookmark list HTML by @sissbruecker in https://github.com/sissbruecker/linkding/pull/332
* Bump python version to 3.10 by @sissbruecker in https://github.com/sissbruecker/linkding/pull/333
* Fix error when deleting all bookmarks in admin by @sissbruecker in https://github.com/sissbruecker/linkding/pull/336
* Improve bookmark query performance by @sissbruecker in https://github.com/sissbruecker/linkding/pull/334
* Prevent rate limit errors in wayback machine API by @sissbruecker in https://github.com/sissbruecker/linkding/pull/339


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.14.0...v1.15.0

---

## v1.14.0 (14/08/2022)

### What's Changed
* Add support for context path by @s2marine in https://github.com/sissbruecker/linkding/pull/313
* Add support for authentication proxies by @sissbruecker in https://github.com/sissbruecker/linkding/pull/321
* Add bookmark list keyboard navigation by @sissbruecker in https://github.com/sissbruecker/linkding/pull/320
* Skip updating website metadata on edit unless URL has changed by @sissbruecker in https://github.com/sissbruecker/linkding/pull/318
* Add simple docs of the new `shared` API parameter by @bachya in https://github.com/sissbruecker/linkding/pull/312
* Add project linka to community section in README by @cmsax in https://github.com/sissbruecker/linkding/pull/319
* Order tags in test_should_create_new_bookmark by @RoGryza in https://github.com/sissbruecker/linkding/pull/310
* Bump django from 3.2.14 to 3.2.15 by @dependabot in https://github.com/sissbruecker/linkding/pull/316

### New Contributors
* @s2marine made their first contribution in https://github.com/sissbruecker/linkding/pull/313
* @RoGryza made their first contribution in https://github.com/sissbruecker/linkding/pull/310
* @cmsax made their first contribution in https://github.com/sissbruecker/linkding/pull/319

**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.13.0...v1.14.0

---

## v1.13.0 (04/08/2022)

### What's Changed
* Add bookmark sharing by @sissbruecker in https://github.com/sissbruecker/linkding/pull/311
* Display selected tags in tag cloud by @sissbruecker and @jhauris in https://github.com/sissbruecker/linkding/pull/307
* Update unread flag when saving duplicate URL by @sissbruecker in https://github.com/sissbruecker/linkding/pull/306


**Full Changelog**: https://github.com/sissbruecker/linkding/compare/v1.12.0...v1.13.0

---

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