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
        self.assertEqual(response.status_code, 302)

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
        expected_url = (
            reverse("bookmarks:edit", args=[bookmark.id]) + "?return_url=/bookmarks"
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
