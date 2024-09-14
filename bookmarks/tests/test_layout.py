from django.test import TestCase
from django.urls import reverse

from bookmarks.models import GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin


class LayoutTestCase(TestCase, BookmarkFactoryMixin):

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
