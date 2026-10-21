from urllib.parse import urlencode

from bs4 import BeautifulSoup
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from bookmarks.models import Bookmark
from bookmarks.tests.helpers import BookmarkFactoryMixin, LinkdingApiTestCase


class FavoriteApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.authenticate()
        self.list_url = reverse("linkding:bookmark-list")

    def test_default_and_serialization(self):
        response = self.post(
            self.list_url + "?disable_scraping",
            {"url": "https://example.com/default"},
            201,
        )
        bookmark = Bookmark.objects.get(pk=response.data["id"])
        self.assertFalse(bookmark.favorite)
        self.assertIs(response.data["favorite"], False)
        detail = self.get(reverse("linkding:bookmark-detail", args=[bookmark.pk]))
        self.assertIs(detail.data["favorite"], False)

    def test_create_favorite(self):
        response = self.post(
            self.list_url + "?disable_scraping",
            {"url": "https://example.com/favorite", "favorite": True},
            201,
        )
        bookmark = Bookmark.objects.get(pk=response.data["id"])
        self.assertTrue(bookmark.favorite)
        self.assertIs(response.data["favorite"], True)

    def test_update_favorite_and_preserve_when_omitted(self):
        bookmark = self.setup_bookmark()
        url = reverse("linkding:bookmark-detail", args=[bookmark.pk])
        for method in (self.patch, self.put):
            for favorite in (True, False):
                with self.subTest(method=method.__name__, favorite=favorite):
                    response = method(url, {"url": bookmark.url, "favorite": favorite})
                    bookmark.refresh_from_db()
                    self.assertEqual(bookmark.favorite, favorite)
                    self.assertIs(response.data["favorite"], favorite)
                    method(url, {"url": bookmark.url, "title": "Updated"})
                    bookmark.refresh_from_db()
                    self.assertEqual(bookmark.favorite, favorite)

    def test_filter_favorite_and_user_isolation(self):
        favorite = self.setup_bookmark(favorite=True, title="matching")
        ordinary = self.setup_bookmark(title="matching")
        other_user = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        self.setup_bookmark(user=other_user, favorite=True, shared=True)
        self.setup_bookmark(user=other_user, favorite=False, shared=True)
        self.setup_bookmark(favorite=True, is_archived=True)
        cases = [
            ({}, [favorite, ordinary]),
            ({"favorite": "true"}, [favorite]),
            ({"favorite": "false"}, [ordinary]),
            ({"favorite": "yes"}, [favorite]),
            ({"favorite": "no"}, [ordinary]),
            ({"favorite": "invalid"}, [favorite, ordinary]),
            ({"favorite": ""}, [favorite, ordinary]),
            ({"favorite": "true", "q": "matching"}, [favorite]),
            ({"favorite": "false", "q": "missing"}, []),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                response = self.get(self.list_url + "?" + urlencode(params))
                self.assertCountEqual(
                    [item["id"] for item in response.data["results"]],
                    [bookmark.pk for bookmark in expected],
                )

    def test_cannot_modify_another_users_favorite(self):
        bookmark = self.setup_bookmark(user=self.setup_user(), shared=True)
        self.patch(
            reverse("linkding:bookmark-detail", args=[bookmark.pk]),
            {"favorite": True},
            404,
        )
        bookmark.refresh_from_db()
        self.assertFalse(bookmark.favorite)

    def test_invalid_favorite_body_is_rejected(self):
        for value in (None, "invalid"):
            with self.subTest(value=value):
                self.post(
                    self.list_url + "?disable_scraping",
                    {"url": "https://example.com/invalid", "favorite": value},
                    400,
                )
        self.assertFalse(Bookmark.objects.exists())

    def test_duplicate_url_updates_favorite(self):
        bookmark = self.setup_bookmark()
        for favorite in (True, False):
            with self.subTest(favorite=favorite):
                response = self.post(
                    self.list_url + "?disable_scraping",
                    {"url": bookmark.url, "favorite": favorite},
                    201,
                )
                self.assertEqual(response.data["id"], bookmark.pk)
                bookmark.refresh_from_db()
                self.assertEqual(bookmark.favorite, favorite)
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_check_returns_existing_favorite_for_form_prefill(self):
        bookmark = self.setup_bookmark(favorite=True)
        response = self.get(
            self.list_url + "check/?" + urlencode({"url": bookmark.url})
        )
        self.assertIs(response.data["bookmark"]["favorite"], True)


class FavoriteWebTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.client.force_login(self.get_or_create_test_user())

    def test_new_bookmark_defaults_to_false(self):
        bookmark = self.setup_bookmark()
        bookmark.refresh_from_db()
        self.assertFalse(bookmark.favorite)

    def test_create_and_edit_favorite_with_existing_form(self):
        form_data = {
            "url": "https://example.com/web-favorite",
            "tag_string": "",
            "favorite": "on",
        }
        response = self.client.post(reverse("linkding:bookmarks.new"), form_data)
        self.assertEqual(response.status_code, 302)
        bookmark = Bookmark.objects.get(url=form_data["url"])
        self.assertTrue(bookmark.favorite)
        edit_url = reverse("linkding:bookmarks.edit", args=[bookmark.pk])
        for favorite in (False, True):
            with self.subTest(favorite=favorite):
                data = {"url": bookmark.url, "tag_string": ""}
                if favorite:
                    data["favorite"] = "on"
                response = self.client.post(edit_url, data, HTTP_TURBO_FRAME="main")
                self.assertEqual(response.status_code, 302)
                bookmark.refresh_from_db()
                self.assertEqual(bookmark.favorite, favorite)
                form = BeautifulSoup(self.client.get(edit_url).content, "html.parser")
                checkbox = form.select_one('input[name="favorite"]')
                self.assertIsNotNone(checkbox)
                self.assertEqual(checkbox.has_attr("checked"), favorite)
                listing = self.client.get(reverse("linkding:bookmarks.index"))
                if favorite:
                    self.assertContains(
                        listing, '<span class="label">Favorite</span>', html=True
                    )
                else:
                    self.assertNotContains(
                        listing, '<span class="label">Favorite</span>', html=True
                    )

    def test_cannot_edit_other_users_favorite(self):
        bookmark = self.setup_bookmark(user=self.setup_user(), shared=True)
        response = self.client.post(
            reverse("linkding:bookmarks.edit", args=[bookmark.pk]),
            {"url": bookmark.url, "tag_string": "", "favorite": "on"},
        )
        self.assertEqual(response.status_code, 404)
        bookmark.refresh_from_db()
        self.assertFalse(bookmark.favorite)

    def test_duplicate_url_preserves_submitted_favorite(self):
        bookmark = self.setup_bookmark()
        response = self.client.post(
            reverse("linkding:bookmarks.new"),
            {"url": bookmark.url, "tag_string": "", "favorite": "on"},
        )
        self.assertEqual(response.status_code, 302)
        bookmark.refresh_from_db()
        self.assertTrue(bookmark.favorite)
        self.assertEqual(Bookmark.objects.count(), 1)


class FavoriteMigrationTestCase(TransactionTestCase):
    def test_existing_bookmark_gets_non_nullable_false_default(self):
        previous = [("bookmarks", "0054_bookmarkbundle_filter_shared_and_more")]
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(previous)
            apps = executor.loader.project_state(previous).apps
            user = apps.get_model("auth", "User").objects.create(
                username="migration-user"
            )
            bookmark = apps.get_model("bookmarks", "Bookmark").objects.create(
                owner_id=user.pk,
                url="https://example.com/existing",
                title="Existing bookmark",
                date_added=timezone.now(),
                date_modified=timezone.now(),
            )
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            migrated = Bookmark.objects.get(pk=bookmark.pk)
            self.assertIs(migrated.favorite, False)
            self.assertEqual(migrated.title, "Existing bookmark")
            self.assertEqual(migrated.owner_id, user.pk)
            field = Bookmark._meta.get_field("favorite")
            self.assertFalse(field.null)
            self.assertIs(field.default, False)
        finally:
            MigrationExecutor(connection).migrate(latest)
