import os
from unittest import mock

from django.test import TestCase

from bookmarks.models import User
from bookmarks.management.commands.create_initial_superuser import Command


class TestCreateInitialSuperuserCommand(TestCase):

    @mock.patch.dict(
        os.environ,
        {"LD_SUPERUSER_NAME": "john", "LD_SUPERUSER_PASSWORD": "password123"},
    )
    def test_create_with_password(self):
        Command().handle()

        self.assertEqual(1, User.objects.count())

        user = User.objects.first()
        self.assertEqual("john", user.username)
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password("password123"))

    @mock.patch.dict(os.environ, {"LD_SUPERUSER_NAME": "john"})
    def test_create_without_password(self):
        Command().handle()

        self.assertEqual(1, User.objects.count())

        user = User.objects.first()
        self.assertEqual("john", user.username)
        self.assertFalse(user.has_usable_password())

    def test_create_without_options(self):
        Command().handle()

        self.assertEqual(0, User.objects.count())

    @mock.patch.dict(
        os.environ,
        {"LD_SUPERUSER_NAME": "john", "LD_SUPERUSER_PASSWORD": "password123"},
    )
    def test_create_multiple_times(self):
        Command().handle()
        Command().handle()
        Command().handle()

        self.assertEqual(1, User.objects.count())
