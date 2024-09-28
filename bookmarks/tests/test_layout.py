from django.test import TestCase
from django.urls import reverse

from bookmarks.models import GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class LayoutTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_nav_menu_should_respect_share_profile_setting(self):
        self.user.profile.enable_sharing = False
        self.user.profile.save()
        response = self.client.get(reverse("bookmarks:index"))
        html = response.content.decode()

        self.assertInHTML(
            f"""
            <a href="{reverse('bookmarks:shared')}" class="menu-link">Shared</a>
        """,
            html,
            count=0,
        )

        self.user.profile.enable_sharing = True
        self.user.profile.save()
        response = self.client.get(reverse("bookmarks:index"))
        html = response.content.decode()

        self.assertInHTML(
            f"""
            <a href="{reverse('bookmarks:shared')}" class="menu-link">Shared</a>
        """,
            html,
            count=2,
        )

    def test_metadata_should_respect_prefetch_links_setting(self):
        settings = GlobalSettings.get()
        settings.enable_link_prefetch = False
        settings.save()

        response = self.client.get(reverse("bookmarks:index"))
        html = response.content.decode()

        self.assertInHTML(
            '<meta name="turbo-prefetch" content="false">',
            html,
            count=1,
        )

        settings.enable_link_prefetch = True
        settings.save()

        response = self.client.get(reverse("bookmarks:index"))
        html = response.content.decode()

        self.assertInHTML(
            '<meta name="turbo-prefetch" content="false">',
            html,
            count=0,
        )

    def test_does_not_link_custom_css_when_empty(self):
        response = self.client.get(reverse("bookmarks:index"))
        html = response.content.decode()
        soup = self.make_soup(html)

        link = soup.select_one("link[rel='stylesheet'][href*='custom_css']")
        self.assertIsNone(link)

    def test_does_link_custom_css_when_not_empty(self):
        profile = self.get_or_create_test_user().profile
        profile.custom_css = "body { background-color: red; }"
        profile.save()

        response = self.client.get(reverse("bookmarks:index"))
        html = response.content.decode()
        soup = self.make_soup(html)

        link = soup.select_one("link[rel='stylesheet'][href*='custom_css']")
        self.assertIsNotNone(link)

    def test_custom_css_link_href(self):
        profile = self.get_or_create_test_user().profile
        profile.custom_css = "body { background-color: red; }"
        profile.save()

        response = self.client.get(reverse("bookmarks:index"))
        html = response.content.decode()
        soup = self.make_soup(html)

        link = soup.select_one("link[rel='stylesheet'][href*='custom_css']")
        expected_url = (
            reverse("bookmarks:custom_css") + f"?hash={profile.custom_css_hash}"
        )
        self.assertEqual(link["href"], expected_url)
