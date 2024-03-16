from django.contrib.auth.models import User
from django.test import TestCase

from bookmarks.models import UserProfile


class UserProfileTestCase(TestCase):

    def test_create_user_should_init_profile(self):
        user = User.objects.create_user("testuser", "test@example.com", "password123")
        profile = UserProfile.objects.all().filter(user_id=user.id).first()
        self.assertIsNotNone(profile)

    def test_bookmark_sharing_is_disabled_by_default(self):
        user = User.objects.create_user("testuser", "test@example.com", "password123")
        profile = UserProfile.objects.all().filter(user_id=user.id).first()
        self.assertFalse(profile.enable_sharing)
