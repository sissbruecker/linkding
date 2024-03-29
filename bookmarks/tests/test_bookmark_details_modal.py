from django.test import TestCase
from django.urls import reverse
from django.utils import formats

from bookmarks.models import UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class BookmarkDetailsModalTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def setUp(self):
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def get_base_url(self, bookmark):
        return reverse("bookmarks:details_modal", args=[bookmark.id])

    def get_details(self, bookmark, return_url=""):
        url = self.get_base_url(bookmark)
        if return_url:
            url += f"?return_url={return_url}"
        response = self.client.get(url)
        soup = self.make_soup(response.content)
        return soup

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

    def test_access(self):
        # own bookmark
        bookmark = self.setup_bookmark()

        response = self.client.get(
            reverse("bookmarks:details_modal", args=[bookmark.id])
        )
        self.assertEqual(response.status_code, 200)

        # other user's bookmark
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)

        response = self.client.get(
            reverse("bookmarks:details_modal", args=[bookmark.id])
        )
        self.assertEqual(response.status_code, 404)

        # non-existent bookmark
        response = self.client.get(reverse("bookmarks:details_modal", args=[9999]))
        self.assertEqual(response.status_code, 404)

        # guest user
        self.client.logout()
        response = self.client.get(
            reverse("bookmarks:details_modal", args=[bookmark.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_access_with_sharing(self):
        # shared bookmark, sharing disabled
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(shared=True, user=other_user)

        response = self.client.get(
            reverse("bookmarks:details_modal", args=[bookmark.id])
        )
        self.assertEqual(response.status_code, 404)

        # shared bookmark, sharing enabled
        profile = other_user.profile
        profile.enable_sharing = True
        profile.save()

        response = self.client.get(
            reverse("bookmarks:details_modal", args=[bookmark.id])
        )
        self.assertEqual(response.status_code, 200)

        # shared bookmark, guest user, no public sharing
        self.client.logout()
        response = self.client.get(
            reverse("bookmarks:details_modal", args=[bookmark.id])
        )
        self.assertEqual(response.status_code, 404)

        # shared bookmark, guest user, public sharing
        profile.enable_public_sharing = True
        profile.save()

        response = self.client.get(
            reverse("bookmarks:details_modal", args=[bookmark.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_displays_title(self):
        # with title
        bookmark = self.setup_bookmark(title="Test title")
        soup = self.get_details(bookmark)

        title = soup.find("h2")
        self.assertIsNotNone(title)
        self.assertEqual(title.text.strip(), bookmark.title)

        # with website title
        bookmark = self.setup_bookmark(title="", website_title="Website title")
        soup = self.get_details(bookmark)

        title = soup.find("h2")
        self.assertIsNotNone(title)
        self.assertEqual(title.text.strip(), bookmark.website_title)

        # with URL only
        bookmark = self.setup_bookmark(title="", website_title="")
        soup = self.get_details(bookmark)

        title = soup.find("h2")
        self.assertIsNotNone(title)
        self.assertEqual(title.text.strip(), bookmark.url)

    def test_website_link(self):
        # basics
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)
        link = self.find_weblink(soup, bookmark.url)
        self.assertIsNotNone(link)
        self.assertEqual(link["href"], bookmark.url)
        self.assertEqual(link.text.strip(), bookmark.url)

        # favicons disabled
        bookmark = self.setup_bookmark(favicon_file="example.png")
        soup = self.get_details(bookmark)
        link = self.find_weblink(soup, bookmark.url)
        image = link.select_one("img")
        self.assertIsNone(image)

        # favicons enabled, no favicon
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = True
        profile.save()

        bookmark = self.setup_bookmark(favicon_file="")
        soup = self.get_details(bookmark)
        link = self.find_weblink(soup, bookmark.url)
        image = link.select_one("img")
        self.assertIsNone(image)

        # favicons enabled, favicon present
        bookmark = self.setup_bookmark(favicon_file="example.png")
        soup = self.get_details(bookmark)
        link = self.find_weblink(soup, bookmark.url)
        image = link.select_one("img")
        self.assertIsNotNone(image)
        self.assertEqual(image["src"], "/static/example.png")

    def test_internet_archive_link(self):
        # without snapshot url
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)
        link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        self.assertIsNone(link)

        # with snapshot url
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com/")
        soup = self.get_details(bookmark)
        link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        self.assertIsNotNone(link)
        self.assertEqual(link["href"], bookmark.web_archive_snapshot_url)
        self.assertEqual(link.text.strip(), "View on Internet Archive")

        # favicons disabled
        bookmark = self.setup_bookmark(
            web_archive_snapshot_url="https://example.com/", favicon_file="example.png"
        )
        soup = self.get_details(bookmark)
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
        soup = self.get_details(bookmark)
        link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        image = link.select_one("svg")
        self.assertIsNone(image)

        # favicons enabled, favicon present
        bookmark = self.setup_bookmark(
            web_archive_snapshot_url="https://example.com/", favicon_file="example.png"
        )
        soup = self.get_details(bookmark)
        link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        image = link.select_one("svg")
        self.assertIsNotNone(image)

    def test_weblinks_respect_target_setting(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com/")

        # target blank
        profile = self.get_or_create_test_user().profile
        profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_BLANK
        profile.save()

        soup = self.get_details(bookmark)

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

        soup = self.get_details(bookmark)

        website_link = self.find_weblink(soup, bookmark.url)
        self.assertIsNotNone(website_link)
        self.assertEqual(website_link["target"], UserProfile.BOOKMARK_LINK_TARGET_SELF)

        web_archive_link = self.find_weblink(soup, bookmark.web_archive_snapshot_url)
        self.assertIsNotNone(web_archive_link)
        self.assertEqual(
            web_archive_link["target"], UserProfile.BOOKMARK_LINK_TARGET_SELF
        )

    def test_status(self):
        # renders form
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Status")

        form = section.find("form")
        self.assertIsNotNone(form)
        self.assertEqual(
            form["action"], reverse("bookmarks:details", args=[bookmark.id])
        )
        self.assertEqual(form["method"], "post")

        # sharing disabled
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)
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
        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Status")

        archived = section.find("input", {"type": "checkbox", "name": "is_archived"})
        self.assertIsNotNone(archived)
        unread = section.find("input", {"type": "checkbox", "name": "unread"})
        self.assertIsNotNone(unread)
        shared = section.find("input", {"type": "checkbox", "name": "shared"})
        self.assertIsNotNone(shared)

        # unchecked
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Status")

        archived = section.find("input", {"type": "checkbox", "name": "is_archived"})
        self.assertFalse(archived.has_attr("checked"))
        unread = section.find("input", {"type": "checkbox", "name": "unread"})
        self.assertFalse(unread.has_attr("checked"))
        shared = section.find("input", {"type": "checkbox", "name": "shared"})
        self.assertFalse(shared.has_attr("checked"))

        # checked
        bookmark = self.setup_bookmark(is_archived=True, unread=True, shared=True)
        soup = self.get_details(bookmark)
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
        soup = self.get_details(bookmark)
        section = self.find_section(soup, "Status")
        form_action = reverse("bookmarks:details", args=[bookmark.id])
        form = soup.find("form", {"action": form_action})
        self.assertIsNotNone(section)
        self.assertIsNotNone(form)

        # other user's bookmark
        other_user = self.setup_user(enable_sharing=True)
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        soup = self.get_details(bookmark)
        section = self.find_section(soup, "Status")
        form_action = reverse("bookmarks:details", args=[bookmark.id])
        form = soup.find("form", {"action": form_action})
        self.assertIsNone(section)
        self.assertIsNone(form)

        # guest user
        self.client.logout()
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        soup = self.get_details(bookmark)
        section = self.find_section(soup, "Status")
        form_action = reverse("bookmarks:details", args=[bookmark.id])
        form = soup.find("form", {"action": form_action})
        self.assertIsNone(section)
        self.assertIsNone(form)

    def test_status_update(self):
        bookmark = self.setup_bookmark()

        # update status
        response = self.client.post(
            self.get_base_url(bookmark),
            {"is_archived": "on", "unread": "on", "shared": "on"},
        )
        self.assertEqual(response.status_code, 302)

        bookmark.refresh_from_db()
        self.assertTrue(bookmark.is_archived)
        self.assertTrue(bookmark.unread)
        self.assertTrue(bookmark.shared)

        # update individual status
        response = self.client.post(
            self.get_base_url(bookmark),
            {"is_archived": "", "unread": "on", "shared": ""},
        )
        self.assertEqual(response.status_code, 302)

        bookmark.refresh_from_db()
        self.assertFalse(bookmark.is_archived)
        self.assertTrue(bookmark.unread)
        self.assertFalse(bookmark.shared)

    def test_status_update_access(self):
        # no sharing
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)
        response = self.client.post(
            self.get_base_url(bookmark),
            {"is_archived": "on", "unread": "on", "shared": "on"},
        )
        self.assertEqual(response.status_code, 404)

        # shared, sharing disabled
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        response = self.client.post(
            self.get_base_url(bookmark),
            {"is_archived": "on", "unread": "on", "shared": "on"},
        )
        self.assertEqual(response.status_code, 404)

        # shared, sharing enabled
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        profile = other_user.profile
        profile.enable_sharing = True
        profile.save()

        response = self.client.post(
            self.get_base_url(bookmark),
            {"is_archived": "on", "unread": "on", "shared": "on"},
        )
        self.assertEqual(response.status_code, 404)

        # shared, public sharing enabled
        bookmark = self.setup_bookmark(user=other_user, shared=True)
        profile = other_user.profile
        profile.enable_public_sharing = True
        profile.save()

        response = self.client.post(
            self.get_base_url(bookmark),
            {"is_archived": "on", "unread": "on", "shared": "on"},
        )
        self.assertEqual(response.status_code, 404)

        # guest user
        self.client.logout()
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        response = self.client.post(
            self.get_base_url(bookmark),
            {"is_archived": "on", "unread": "on", "shared": "on"},
        )
        self.assertEqual(response.status_code, 404)

    def test_date_added(self):
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Date added")

        expected_date = formats.date_format(bookmark.date_added, "DATETIME_FORMAT")
        date = section.find("span", string=expected_date)
        self.assertIsNotNone(date)

    def test_tags(self):
        # without tags
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)

        section = self.find_section(soup, "Tags")
        self.assertIsNone(section)

        # with tags
        bookmark = self.setup_bookmark(tags=[self.setup_tag(), self.setup_tag()])

        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Tags")

        for tag in bookmark.tags.all():
            tag_link = section.find("a", string=f"#{tag.name}")
            self.assertIsNotNone(tag_link)
            expected_url = reverse("bookmarks:index") + f"?q=%23{tag.name}"
            self.assertEqual(tag_link["href"], expected_url)

    def test_description(self):
        # without description
        bookmark = self.setup_bookmark(description="", website_description="")
        soup = self.get_details(bookmark)

        section = self.find_section(soup, "Description")
        self.assertIsNone(section)

        # with description
        bookmark = self.setup_bookmark(description="Test description")
        soup = self.get_details(bookmark)

        section = self.get_section(soup, "Description")
        self.assertEqual(section.text.strip(), bookmark.description)

        # with website description
        bookmark = self.setup_bookmark(
            description="", website_description="Website description"
        )
        soup = self.get_details(bookmark)

        section = self.get_section(soup, "Description")
        self.assertEqual(section.text.strip(), bookmark.website_description)

    def test_notes(self):
        # without notes
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)

        section = self.find_section(soup, "Notes")
        self.assertIsNone(section)

        # with notes
        bookmark = self.setup_bookmark(notes="Test notes")
        soup = self.get_details(bookmark)

        section = self.get_section(soup, "Notes")
        self.assertEqual(section.decode_contents(), "<p>Test notes</p>")

    def test_edit_link(self):
        bookmark = self.setup_bookmark()

        # with default return URL
        soup = self.get_details(bookmark)
        edit_link = soup.find("a", string="Edit")
        self.assertIsNotNone(edit_link)
        details_url = reverse("bookmarks:details", args=[bookmark.id])
        expected_url = (
            reverse("bookmarks:edit", args=[bookmark.id]) + "?return_url=" + details_url
        )
        self.assertEqual(edit_link["href"], expected_url)

        # with custom return URL
        soup = self.get_details(bookmark, return_url="/custom")
        edit_link = soup.find("a", string="Edit")
        self.assertIsNotNone(edit_link)
        expected_url = (
            reverse("bookmarks:edit", args=[bookmark.id]) + "?return_url=/custom"
        )
        self.assertEqual(edit_link["href"], expected_url)

    def test_delete_button(self):
        bookmark = self.setup_bookmark()

        # basics
        soup = self.get_details(bookmark)
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNotNone(delete_button)
        self.assertEqual(delete_button.text.strip(), "Delete...")
        self.assertEqual(delete_button["value"], str(bookmark.id))

        form = delete_button.find_parent("form")
        self.assertIsNotNone(form)
        expected_url = reverse("bookmarks:index.action") + f"?return_url=/bookmarks"
        self.assertEqual(form["action"], expected_url)

        # with custom return URL
        soup = self.get_details(bookmark, return_url="/custom")
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        form = delete_button.find_parent("form")
        expected_url = reverse("bookmarks:index.action") + f"?return_url=/custom"
        self.assertEqual(form["action"], expected_url)

    def test_actions_visibility(self):
        # with sharing
        other_user = self.setup_user(enable_sharing=True)
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        soup = self.get_details(bookmark)
        edit_link = soup.find("a", string="Edit")
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNone(edit_link)
        self.assertIsNone(delete_button)

        # with public sharing
        profile = other_user.profile
        profile.enable_public_sharing = True
        profile.save()
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        soup = self.get_details(bookmark)
        edit_link = soup.find("a", string="Edit")
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNone(edit_link)
        self.assertIsNone(delete_button)

        # guest user
        self.client.logout()
        bookmark = self.setup_bookmark(user=other_user, shared=True)

        soup = self.get_details(bookmark)
        edit_link = soup.find("a", string="Edit")
        delete_button = soup.find("button", {"type": "submit", "name": "remove"})
        self.assertIsNone(edit_link)
        self.assertIsNone(delete_button)
