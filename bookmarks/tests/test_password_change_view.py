from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from bookmarks.tests.helpers import BookmarkFactoryMixin


class PasswordChangeViewTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            "testuser", "test@example.com", "initial_password"
        )
        self.client.force_login(self.user)

    def test_change_password(self):
        form_data = {
            "old_password": "initial_password",
            "new_password1": "new_password",
            "new_password2": "new_password",
        }

        response = self.client.post(reverse("change_password"), form_data)

        self.assertRedirects(response, reverse("password_change_done"))

    def test_change_password_done(self):
        form_data = {
            "old_password": "initial_password",
            "new_password1": "new_password",
            "new_password2": "new_password",
        }

        response = self.client.post(reverse("change_password"), form_data, follow=True)

        self.assertContains(response, "Your password was changed successfully")

    def test_should_return_error_for_invalid_old_password(self):
        form_data = {
            "old_password": "wrong_password",
            "new_password1": "new_password",
            "new_password2": "new_password",
        }

        response = self.client.post(reverse("change_password"), form_data)

        self.assertEqual(response.status_code, 422)
        self.assertIn("old_password", response.context_data["form"].errors)

    def test_should_return_error_for_mismatching_new_password(self):
        form_data = {
            "old_password": "initial_password",
            "new_password1": "new_password",
            "new_password2": "wrong_password",
        }

        response = self.client.post(reverse("change_password"), form_data)

        self.assertEqual(response.status_code, 422)
        self.assertIn("new_password2", response.context_data["form"].errors)
