from django.test import TestCase

from bookmarks.tests.helpers import BookmarkFactoryMixin


class AdminBackgroundTasksViewTestCase(TestCase, BookmarkFactoryMixin):
    url = "/admin/tasks/"

    def test_should_redirect_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response, f"/admin/login/?next={self.url}", fetch_redirect_response=False
        )

    def test_should_redirect_non_staff_user_to_login(self):
        user = self.setup_user()
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertRedirects(
            response, f"/admin/login/?next={self.url}", fetch_redirect_response=False
        )

    def test_should_redirect_inactive_staff_user_to_login(self):
        user = self.setup_user()
        user.is_staff = True
        user.is_active = False
        user.save()
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertRedirects(
            response, f"/admin/login/?next={self.url}", fetch_redirect_response=False
        )

    def test_should_allow_staff_user(self):
        user = self.setup_user()
        user.is_staff = True
        user.save()
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Background tasks")

    def test_should_allow_superuser(self):
        superuser = self.setup_superuser()
        self.client.force_login(superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Background tasks")
