import datetime
import re

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import formats, timezone

from bookmarks.models import BookmarkAsset, UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class BookmarkDetailsModalTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def setUp(self):
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def get_details_form(self, soup, bookmark):
        form_url = reverse("bookmarks:index.action") + f"?details={bookmark.id}"
        return soup.find("form", {"action": form_url, "enctype": "multipart/form-data"})

    def get_index_details_modal(self, bookmark):
        url = reverse("bookmarks:index") + f"?details={bookmark.id}"
        response = self.client.get(url)
        soup = self.make_soup(response.content)
        modal = soup.find("turbo-frame", {"id": "details-modal"})
        return modal

    def get_shared_details_modal(self, bookmark):
        url = reverse("bookmarks:shared") + f"?details={bookmark.id}"
        response = self.client.get(url)
        soup = self.make_soup(response.content)
        modal = soup.find("turbo-frame", {"id": "details-modal"})
        return modal

    def find_section(self, soup, section_name):
        dt = soup.find("dt", string=section_name)
        dd = dt.find_next_sibling("dd") if dt else None
        return dd

    def get_section(self, soup, section_name):
        dd = self.find_section(soup, section_name)
        self.assertIsNotNone(dd)
        return dd

    def find_weblink(self, soup, url):
        return soup.find("a", {"class": "weblink", "href": url})

    def count_weblinks(self, soup):
        return len(soup.find_all("a", {"class": "weblink"}))

    def find_asset(self, soup, asset):
        return soup.find("div", {"data-asset-id": asset.id})

    def details_route_access_test(self):
        # own bookmark
        bookmark = self.setup_bookmark()
        response = self.client.get(
            reverse("bookmarks:index") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 200)

        # other user's bookmark
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        response = self.client.get(
            reverse("bookmarks:index") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 404)

        # non-existent bookmark - just returns without modal in response
        response = self.client.get(reverse("bookmarks:index") + "?details=9999")
        self.assertEqual(response.status_code, 200)

        # guest user
        self.client.logout()
        response = self.client.get(
            reverse("bookmarks:shared") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 404)

    def test_access(self):
        # own bookmark
        bookmark = self.setup_bookmark()
        response = self.client.get(
            reverse("bookmarks:index") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 200)

        # other user's bookmark
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        response = self.client.get(
            reverse("bookmarks:index") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 404)

        # non-existent bookmark - just returns without modal in response
        response = self.client.get(reverse("bookmarks:index") + "?details=9999")
        self.assertEqual(response.status_code, 200)

        # guest user
        self.client.logout()
        response = self.client.get(
            reverse("bookmarks:shared") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 404)

    def test_access_with_sharing(self):
        # shared bookmark, sharing disabled
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(shared=True, user=other_user)

        response = self.client.get(
            reverse("bookmarks:shared") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 404)

        # shared bookmark, sharing enabled
        profile = other_user.profile
        profile.enable_sharing = True
        profile.save()

        response = self.client.get(
            reverse("bookmarks:shared") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 200)

        # shared bookmark, guest user, no public sharing
        self.client.logout()
        response = self.client.get(
            reverse("bookmarks:shared") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 404)

        # shared bookmark, guest user, public sharing
        profile.enable_public_sharing = True
        profile.save()

        response = self.client.get(
            reverse("bookmarks:shared") + f"?details={bookmark.id}"
        )
        self.assertEqual(response.status_code, 200)

    def test_displays_title(self):
        # with title
        bookmark = self.setup_bookmark(title="Test title")
        soup = self.get_index_details_modal(bookmark)

        title = soup.find("h2")
        self.assertIsNotNone(title)
        self.assertEqual(title.text.strip(), bookmark.title)

        # with URL only
        bookmark = self.setup_bookmark(title="")
        soup = self.get_index_details_modal(bookmark)

        title = soup.find("h2")
        self.assertIsNotNone(title)
        self.assertEqual(title.text.strip(), bookmark.url)

    def test_website_link(self):
        # basics
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, bookmark.url)
        self.assertIsNotNone(link)
        self.assertEqual(link["href"], bookmark.url)
        self.assertEqual(link.text.strip(), bookmark.url)

        # favicons disabled
        bookmark = self.setup_bookmark(favicon_file="example.png")
        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, bookmark.url)
        image = link.select_one("img")
        self.assertIsNone(image)

        # favicons enabled, no favicon
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = True
        profile.save()

        bookmark = self.setup_bookmark(favicon_file="")
        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, bookmark.url)
        image = link.select_one("img")
        self.assertIsNone(image)

        # favicons enabled, favicon present
        bookmark = self.setup_bookmark(favicon_file="example.png")
        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, bookmark.url)
        image = link.select_one("img")
        self.assertIsNotNone(image)
        self.assertEqual(image["src"], "/static/example.png")

    def test_reader_mode_link(self):
        # no latest snapshot
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        self.assertEqual(self.count_weblinks(soup), 2)

        # snapshot is not complete
        self.setup_asset(
            bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_PENDING,
        )
        self.setup_asset(
            bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_FAILURE,
        )
        soup = self.get_index_details_modal(bookmark)
        self.assertEqual(self.count_weblinks(soup), 2)

        # not a snapshot
        self.setup_asset(
            bookmark,
            asset_type="upload",
            status=BookmarkAsset.STATUS_COMPLETE,
        )
        soup = self.get_index_details_modal(bookmark)
        self.assertEqual(self.count_weblinks(soup), 2)

        # snapshot is complete
        asset = self.setup_asset(
            bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_COMPLETE,
        )
        soup = self.get_index_details_modal(bookmark)
        self.assertEqual(self.count_weblinks(soup), 3)

        reader_mode_url = reverse("bookmarks:assets.read", args=[asset.id])
        link = self.find_weblink(soup, reader_mode_url)
        self.assertIsNotNone(link)

    def test_internet_archive_link_with_snapshot_url(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com/")
        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        self.assertIsNotNone(link)
        self.assertEqual(link["href"], bookmark.web_archive_snapshot_url)
        self.assertEqual(link.text.strip(), "Internet Archive")

        # favicons disabled
        bookmark = self.setup_bookmark(
            web_archive_snapshot_url="https://example.com/", favicon_file="example.png"
        )
        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        image = link.select_one("svg")
        self.assertIsNone(image)

        # favicons enabled, no favicon
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = True
        profile.save()

        bookmark = self.setup_bookmark(
            web_archive_snapshot_url="https://example.com/", favicon_file=""
        )
        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        image = link.select_one("svg")
        self.assertIsNone(image)

        # favicons enabled, favicon present
        bookmark = self.setup_bookmark(
            web_archive_snapshot_url="https://example.com/", favicon_file="example.png"
        )
        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        image = link.select_one("svg")
        self.assertIsNotNone(image)

    def test_internet_archive_link_with_fallback_url(self):
        date_added = timezone.datetime(
            2023, 8, 11, 21, 45, 11, tzinfo=datetime.timezone.utc
        )
        bookmark = self.setup_bookmark(url="https://example.com/", added=date_added)
        fallback_web_archive_url = (
            "https://web.archive.org/web/20230811214511/https://example.com/"
        )

        soup = self.get_index_details_modal(bookmark)
        link = self.find_weblink(soup, fallback_web_archive_url)
        self.assertIsNotNone(link)
        self.assertEqual(link["href"], fallback_web_archive_url)
        self.assertEqual(link.text.strip(), "Internet Archive")

    def test_weblinks_respect_target_setting(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com/")

        # target blank
        profile = self.get_or_create_test_user().profile
        profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_BLANK
        profile.save()

        soup = self.get_index_details_modal(bookmark)

        website_link = self.find_weblink(soup, bookmark.url)
        self.assertIsNotNone(website_link)
        self.assertEqual(website_link["target"], UserProfile.BOOKMARK_LINK_TARGET_BLANK)

        web_archive_link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        self.assertIsNotNone(web_archive_link)
        self.assertEqual(
            web_archive_link["target"], UserProfile.BOOKMARK_LINK_TARGET_BLANK
        )

        # target self
        profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_SELF
        profile.save()

        soup = self.get_index_details_modal(bookmark)

        website_link = self.find_weblink(soup, bookmark.url)
        self.assertIsNotNone(website_link)
        self.assertEqual(website_link["target"], UserProfile.BOOKMARK_LINK_TARGET_SELF)

        web_archive_link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        self.assertIsNotNone(web_archive_link)
        self.assertEqual(
            web_archive_link["target"], UserProfile.BOOKMARK_LINK_TARGET_SELF
        )

    def test_preview_image(self):
        # without image
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        image = soup.select_one("div.preview-image img")
        self.assertIsNone(image)

        # with image
        bookmark = self.setup_bookmark(preview_image_file="example.png")
        soup = self.get_index_details_modal(bookmark)
        image = soup.select_one("div.preview-image img")
        self.assertIsNone(image)

        # preview images enabled, no image
        profile = self.get_or_create_test_user().profile
        profile.enable_preview_images = True
        profile.save()

        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        image = soup.select_one("div.preview-image img")
        self.assertIsNone(image)

        # preview images enabled, image present
        bookmark = self.setup_bookmark(preview_image_file="example.png")
        soup = self.get_index_details_modal(bookmark)
        image = soup.select_one("div.preview-image img")
        self.assertIsNotNone(image)
        self.assertEqual(image["src"], "/static/example.png")

    def test_status(self):
        # renders form
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)

        form = self.get_details_form(soup, bookmark)
        self.assertIsNotNone(form)
        self.assertEqual(form["method"], "post")

        # sharing disabled
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Status")

        archived = section.find("input", {"type": "checkbox", "name": "is_archived"})
        self.assertIsNotNone(archived)
        unread = section.find("input", {"type": "checkbox", "name": "unread"})
        self.assertIsNotNone(unread)
        shared = section.find("input", {"type": "checkbox", "name": "shared"})
        self.assertIsNone(shared)

        # sharing enabled
        profile = self.get_or_create_test_user().profile
        profile.enable_sharing = True
        profile.save()

        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Status")

        archived = section.find("input", {"type": "checkbox", "name": "is_archived"})
        self.assertIsNotNone(archived)
        unread = section.find("input", {"type": "checkbox", "name": "unread"})
        self.assertIsNotNone(unread)
        shared = section.find("input", {"type": "checkbox", "name": "shared"})
        self.assertIsNotNone(shared)

        # unchecked
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Status")

        archived = section.find("input", {"type": "checkbox", "name": "is_archived"})
        self.assertFalse(archived.has_attr("checked"))
        unread = section.find("input", {"type": "checkbox", "name": "unread"})
        self.assertFalse(unread.has_attr("checked"))
        shared = section.find("input", {"type": "checkbox", "name": "shared"})
        self.assertFalse(shared.has_attr("checked"))

        # checked
        bookmark = self.setup_bookmark(is_archived=True, unread=True, shared=True)
        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Status")

        archived = section.find("input", {"type": "checkbox", "name": "is_archived"})
        self.assertTrue(archived.has_attr("checked"))
        unread = section.find("input", {"type": "checkbox", "name": "unread"})
        self.assertTrue(unread.has_attr("checked"))
        shared = section.find("input", {"type": "checkbox", "name": "shared"})
        self.assertTrue(shared.has_attr("checked"))

    def test_status_visibility(self):
        # own bookmark
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        section = self.find_section(soup, "Status")
        self.assertIsNotNone(section)

        # other user's bookmark
        other_user = self.setup_user(enable_sharing=True)
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        soup = self.get_shared_details_modal(bookmark)
        section = self.find_section(soup, "Status")
        self.assertIsNone(section)

        # guest user
        self.client.logout()
        other_user.profile.enable_public_sharing = True
        other_user.profile.save()
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        soup = self.get_shared_details_modal(bookmark)
        section = self.find_section(soup, "Status")
        self.assertIsNone(section)

    def test_date_added(self):
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Date added")

        expected_date = formats.date_format(bookmark.date_added, "DATETIME_FORMAT")
        date = section.find("span", string=expected_date)
        self.assertIsNotNone(date)

    def test_tags(self):
        # without tags
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)

        section = self.find_section(soup, "Tags")
        self.assertIsNone(section)

        # with tags
        bookmark = self.setup_bookmark(tags=[self.setup_tag(), self.setup_tag()])

        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Tags")

        for tag in bookmark.tags.all():
            tag_link = section.find("a", string=f"#{tag.name}")
            self.assertIsNotNone(tag_link)
            expected_url = reverse("bookmarks:index") + f"?q=%23{tag.name}"
            self.assertEqual(tag_link["href"], expected_url)

    def test_description(self):
        # without description
        bookmark = self.setup_bookmark(description="")
        soup = self.get_index_details_modal(bookmark)

        section = self.find_section(soup, "Description")
        self.assertIsNone(section)

        # with description
        bookmark = self.setup_bookmark(description="Test description")
        soup = self.get_index_details_modal(bookmark)

        section = self.get_section(soup, "Description")
        self.assertEqual(section.text.strip(), bookmark.description)

    def test_notes(self):
        # without notes
        bookmark = self.setup_bookmark()
        soup = self.get_index_details_modal(bookmark)

        section = self.find_section(soup, "Notes")
        self.assertIsNone(section)

        # with notes
        bookmark = self.setup_bookmark(notes="Test notes")
        soup = self.get_index_details_modal(bookmark)

        section = self.get_section(soup, "Notes")
        self.assertEqual(section.decode_contents(), "<p>Test notes</p>")

    def test_edit_link(self):
        bookmark = self.setup_bookmark()

        # with default return URL
        soup = self.get_index_details_modal(bookmark)
        edit_link = soup.find("a", string="Edit")
        self.assertIsNotNone(edit_link)
        expected_url = f"/bookmarks/{bookmark.id}/edit?return_url=/bookmarks%3Fdetails%3D{bookmark.id}"
        self.assertEqual(expected_url, edit_link["href"])

    def test_delete_button(self):
        bookmark = self.setup_bookmark()

        modal = self.get_index_details_modal(bookmark)
        delete_button = modal.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNotNone(delete_button)
        self.assertEqual("Delete...", delete_button.text.strip())
        self.assertEqual(str(bookmark.id), delete_button["value"])

        form = delete_button.find_parent("form")
        self.assertIsNotNone(form)
        expected_url = reverse("bookmarks:index.action")
        self.assertEqual(expected_url, form["action"])

    def test_actions_visibility(self):
        # own bookmark
        bookmark = self.setup_bookmark()

        soup = self.get_index_details_modal(bookmark)
        edit_link = soup.find("a", string="Edit")
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNotNone(edit_link)
        self.assertIsNotNone(delete_button)

        # with sharing
        other_user = self.setup_user(enable_sharing=True)
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        soup = self.get_shared_details_modal(bookmark)
        edit_link = soup.find("a", string="Edit")
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNone(edit_link)
        self.assertIsNone(delete_button)

        # with public sharing
        profile = other_user.profile
        profile.enable_public_sharing = True
        profile.save()
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        soup = self.get_shared_details_modal(bookmark)
        edit_link = soup.find("a", string="Edit")
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNone(edit_link)
        self.assertIsNone(delete_button)

        # guest user
        self.client.logout()
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        soup = self.get_shared_details_modal(bookmark)
        edit_link = soup.find("a", string="Edit")
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNone(edit_link)
        self.assertIsNone(delete_button)

    def test_assets_visibility_no_snapshot_support(self):
        bookmark = self.setup_bookmark()

        soup = self.get_index_details_modal(bookmark)
        section = self.find_section(soup, "Files")
        self.assertIsNone(section)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_assets_visibility_with_snapshot_support(self):
        bookmark = self.setup_bookmark()

        soup = self.get_index_details_modal(bookmark)
        section = self.find_section(soup, "Files")
        self.assertIsNotNone(section)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_asset_list_visibility(self):
        # no assets
        bookmark = self.setup_bookmark()

        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Files")
        asset_list = section.find("div", {"class": "assets"})
        self.assertIsNone(asset_list)

        # with assets
        bookmark = self.setup_bookmark()
        self.setup_asset(bookmark)

        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Files")
        asset_list = section.find("div", {"class": "assets"})
        self.assertIsNotNone(asset_list)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_asset_list(self):
        bookmark = self.setup_bookmark()
        assets = [
            self.setup_asset(bookmark),
            self.setup_asset(bookmark),
            self.setup_asset(bookmark),
        ]

        soup = self.get_index_details_modal(bookmark)
        section = self.get_section(soup, "Files")
        asset_list = section.find("div", {"class": "assets"})

        for asset in assets:
            asset_item = self.find_asset(asset_list, asset)
            self.assertIsNotNone(asset_item)

            asset_icon = asset_item.select_one(".asset-icon svg")
            self.assertIsNotNone(asset_icon)

            asset_text = asset_item.select_one(".asset-text span")
            self.assertIsNotNone(asset_text)
            self.assertIn(asset.display_name, asset_text.text)

            view_url = reverse("bookmarks:assets.view", args=[asset.id])
            view_link = asset_item.find("a", {"href": view_url})
            self.assertIsNotNone(view_link)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_asset_without_file(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(bookmark)
        asset.file = ""
        asset.save()

        soup = self.get_index_details_modal(bookmark)
        asset_item = self.find_asset(soup, asset)
        view_url = reverse("bookmarks:assets.view", args=[asset.id])
        view_link = asset_item.find("a", {"href": view_url})
        self.assertIsNone(view_link)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_asset_status(self):
        bookmark = self.setup_bookmark()
        pending_asset = self.setup_asset(bookmark, status=BookmarkAsset.STATUS_PENDING)
        failed_asset = self.setup_asset(bookmark, status=BookmarkAsset.STATUS_FAILURE)

        soup = self.get_index_details_modal(bookmark)

        asset_item = self.find_asset(soup, pending_asset)
        asset_text = asset_item.select_one(".asset-text span")
        self.assertIn("(queued)", asset_text.text)

        asset_item = self.find_asset(soup, failed_asset)
        asset_text = asset_item.select_one(".asset-text span")
        self.assertIn("(failed)", asset_text.text)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_asset_file_size(self):
        bookmark = self.setup_bookmark()
        asset1 = self.setup_asset(bookmark, file_size=None)
        asset2 = self.setup_asset(bookmark, file_size=54639)
        asset3 = self.setup_asset(bookmark, file_size=11492020)

        soup = self.get_index_details_modal(bookmark)

        asset_item = self.find_asset(soup, asset1)
        asset_text = asset_item.select_one(".asset-text")
        self.assertEqual(asset_text.text.strip(), asset1.display_name)

        asset_item = self.find_asset(soup, asset2)
        asset_text = asset_item.select_one(".asset-text")
        self.assertIn("53.4\xa0KB", asset_text.text)

        asset_item = self.find_asset(soup, asset3)
        asset_text = asset_item.select_one(".asset-text")
        self.assertIn("11.0\xa0MB", asset_text.text)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_asset_actions_visibility(self):
        bookmark = self.setup_bookmark()

        # with file
        asset = self.setup_asset(bookmark)
        soup = self.get_index_details_modal(bookmark)

        asset_item = self.find_asset(soup, asset)
        view_link = asset_item.find("a", string="View")
        delete_button = asset_item.find(
            "button", {"type": "submit", "name": "remove_asset"}
        )
        self.assertIsNotNone(view_link)
        self.assertIsNotNone(delete_button)

        # without file
        asset.file = ""
        asset.save()
        soup = self.get_index_details_modal(bookmark)

        asset_item = self.find_asset(soup, asset)
        view_link = asset_item.find("a", string="View")
        delete_button = asset_item.find(
            "button", {"type": "submit", "name": "remove_asset"}
        )
        self.assertIsNone(view_link)
        self.assertIsNotNone(delete_button)

        # shared bookmark
        other_user = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        bookmark = self.setup_bookmark(shared=True, user=other_user)
        asset = self.setup_asset(bookmark)
        soup = self.get_index_details_modal(bookmark)

        asset_item = self.find_asset(soup, asset)
        view_link = asset_item.find("a", string="View")
        delete_button = asset_item.find(
            "button", {"type": "submit", "name": "remove_asset"}
        )
        self.assertIsNotNone(view_link)
        self.assertIsNone(delete_button)

        # shared bookmark, guest user
        self.client.logout()
        soup = self.get_shared_details_modal(bookmark)

        asset_item = self.find_asset(soup, asset)
        view_link = asset_item.find("a", string="View")
        delete_button = asset_item.find(
            "button", {"type": "submit", "name": "remove_asset"}
        )
        self.assertIsNotNone(view_link)
        self.assertIsNone(delete_button)

    @override_settings(LD_ENABLE_SNAPSHOTS=True)
    def test_create_snapshot_is_disabled_when_having_pending_asset(self):
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(bookmark, status=BookmarkAsset.STATUS_COMPLETE)

        # no pending asset
        soup = self.get_index_details_modal(bookmark)
        files_section = self.find_section(soup, "Files")
        create_button = files_section.find(
            "button", string=re.compile("Create HTML snapshot")
        )
        self.assertFalse(create_button.has_attr("disabled"))

        # with pending asset
        asset.status = BookmarkAsset.STATUS_PENDING
        asset.save()

        soup = self.get_index_details_modal(bookmark)
        files_section = self.find_section(soup, "Files")
        create_button = files_section.find(
            "button", string=re.compile("Create HTML snapshot")
        )
        self.assertTrue(create_button.has_attr("disabled"))
