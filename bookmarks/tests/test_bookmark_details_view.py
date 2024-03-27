from django.test import TestCase
from django.urls import reverse
from django.utils import formats

from bookmarks.models import UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class BookmarkDetailsViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def setUp(self):
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def get_details(self, bookmark):
        response = self.client.get(reverse("bookmarks:details", args=[bookmark.id]))
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

    def test_access(self):
        # own bookmark
        bookmark = self.setup_bookmark()

        response = self.client.get(reverse("bookmarks:details", args=[bookmark.id]))
        self.assertEqual(response.status_code, 200)

        # other user's bookmark
        other_user = self.setup_user()
        bookmark = self.setup_bookmark(user=other_user)

        response = self.client.get(reverse("bookmarks:details", args=[bookmark.id]))
        self.assertEqual(response.status_code, 404)

        # guest user
        self.client.logout()
        response = self.client.get(reverse("bookmarks:details", args=[bookmark.id]))
        self.assertEqual(response.status_code, 302)

    def test_return_404_for_non_existent_bookmark(self):
        response = self.client.get(reverse("bookmarks:details", args=[9999]))
        self.assertEqual(response.status_code, 404)

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

    def test_favicon(self):
        # favicons disabled, should not render
        bookmark = self.setup_bookmark(favicon_file="example.png")
        soup = self.get_details(bookmark)

        favicon = soup.select_one("h2 img")
        self.assertIsNone(favicon)

        # favicons enabled, no favicon, should not render
        profile = self.get_or_create_test_user().profile
        profile.enable_favicons = True
        profile.save()

        bookmark = self.setup_bookmark(favicon_file="")
        soup = self.get_details(bookmark)

        favicon = soup.select_one("h2 img")
        self.assertIsNone(favicon)

        # favicons enabled, favicon present, should render
        bookmark = self.setup_bookmark(favicon_file="example.png")
        soup = self.get_details(bookmark)

        favicon = soup.select_one("h2 img")
        self.assertIsNotNone(favicon)
        self.assertEqual(favicon["src"], "/static/example.png")

    def test_link(self):
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)

        link = soup.find("a", string=bookmark.url)
        self.assertIsNotNone(link)
        self.assertEqual(link["href"], bookmark.url)

    def test_link_respects_target_setting(self):
        bookmark = self.setup_bookmark()

        # target blank
        profile = self.get_or_create_test_user().profile
        profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_BLANK
        profile.save()

        soup = self.get_details(bookmark)

        link = soup.find("a", string=bookmark.url)
        self.assertIsNotNone(link)
        self.assertEqual(link["target"], UserProfile.BOOKMARK_LINK_TARGET_BLANK)

        # target self
        profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_SELF
        profile.save()

        soup = self.get_details(bookmark)

        link = soup.find("a", string=bookmark.url)
        self.assertIsNotNone(link)
        self.assertEqual(link["target"], UserProfile.BOOKMARK_LINK_TARGET_SELF)

    def test_date_added(self):
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Date added")

        expected_date = formats.date_format(bookmark.date_added, "DATETIME_FORMAT")
        date = section.find("span", string=expected_date)
        self.assertIsNotNone(date)

    def test_web_archive_link(self):
        # without web archive link
        bookmark = self.setup_bookmark()
        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Date added")

        link = section.find("a", string="View snapshot on Internet Archive")
        self.assertIsNone(link)

        # with web archive link
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com/")
        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Date added")

        link = section.find("a", string="View snapshot on Internet Archive")
        self.assertIsNotNone(link)
        self.assertEqual(link["href"], bookmark.web_archive_snapshot_url)

    def test_web_archive_link_respects_target_setting(self):
        bookmark = self.setup_bookmark(web_archive_snapshot_url="https://example.com/")

        # target blank
        profile = self.get_or_create_test_user().profile
        profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_BLANK
        profile.save()

        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Date added")

        link = section.find("a", string="View snapshot on Internet Archive")
        self.assertIsNotNone(link)
        self.assertEqual(link["target"], UserProfile.BOOKMARK_LINK_TARGET_BLANK)

        # target self
        profile.bookmark_link_target = UserProfile.BOOKMARK_LINK_TARGET_SELF
        profile.save()

        soup = self.get_details(bookmark)
        section = self.get_section(soup, "Date added")

        link = section.find("a", string="View snapshot on Internet Archive")
        self.assertIsNotNone(link)
        self.assertEqual(link["target"], UserProfile.BOOKMARK_LINK_TARGET_SELF)

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
