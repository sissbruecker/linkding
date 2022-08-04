from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class NavMenuTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def test_should_respect_share_profile_setting(self):
        self.user.profile.enable_sharing = False
        self.user.profile.save()
        response = self.client.get(reverse('bookmarks:index'))
        html = response.content.decode()

        self.assertInHTML(f'''
            <a href="{reverse('bookmarks:shared')}" class="btn btn-link">Shared</a>
        ''', html, count=0)

        self.user.profile.enable_sharing = True
        self.user.profile.save()
        response = self.client.get(reverse('bookmarks:index'))
        html = response.content.decode()

        self.assertInHTML(f'''
            <a href="{reverse('bookmarks:shared')}" class="btn btn-link">Shared</a>
        ''', html, count=2)
