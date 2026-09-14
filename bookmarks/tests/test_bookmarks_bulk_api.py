from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from bookmarks.models import Bookmark, GlobalSettings
from bookmarks.tests.helpers import BookmarkFactoryMixin, LinkdingApiTestCase


class BookmarksBulkApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    actions = [("bulk-archive", True), ("bulk-unarchive", False)]

    def test_updates_only_selected_bookmarks(self):
        self.authenticate()
        old_time = timezone.now() - timedelta(days=1)
        tag = self.setup_tag()
        for action, archived in self.actions:
            with self.subTest(action=action):
                selected = [
                    self.setup_bookmark(
                        is_archived=not archived,
                        modified=old_time,
                        tags=[tag],
                        unread=True,
                        shared=True,
                        notes="Keep these notes",
                    )
                    for _ in range(3)
                ]
                untouched = self.setup_bookmark(
                    is_archived=not archived, modified=old_time
                )
                response = self.post(
                    reverse(f"linkding:bookmark-{action}"),
                    {"bookmark_ids": [bookmark.id for bookmark in selected]},
                    status.HTTP_204_NO_CONTENT,
                )
                self.assertEqual(response.content, b"")
                for bookmark in selected:
                    bookmark.refresh_from_db()
                    self.assertEqual(bookmark.is_archived, archived)
                    self.assertGreater(bookmark.date_modified, old_time)
                    self.assertTrue(bookmark.unread)
                    self.assertTrue(bookmark.shared)
                    self.assertEqual(bookmark.notes, "Keep these notes")
                    self.assertEqual(list(bookmark.tags.all()), [tag])
                untouched.refresh_from_db()
                self.assertEqual(untouched.is_archived, not archived)
                self.assertEqual(untouched.date_modified, old_time)

    def test_requires_authentication(self):
        for action, archived in self.actions:
            with self.subTest(action=action):
                bookmark = self.setup_bookmark(is_archived=not archived)
                self.post(
                    reverse(f"linkding:bookmark-{action}"),
                    {"bookmark_ids": [bookmark.id]},
                    status.HTTP_401_UNAUTHORIZED,
                )
                bookmark.refresh_from_db()
                self.assertEqual(bookmark.is_archived, not archived)

    def test_ignores_other_users_and_missing_bookmarks(self):
        self.authenticate()
        other_user = self.setup_user(enable_sharing=True)
        for action, archived in self.actions:
            with self.subTest(action=action):
                own = self.setup_bookmark(is_archived=not archived)
                other = self.setup_bookmark(
                    user=other_user, is_archived=not archived, shared=True
                )
                other_modified = other.date_modified
                missing = self.setup_bookmark()
                missing_id = missing.id
                missing.delete()
                self.post(
                    reverse(f"linkding:bookmark-{action}"),
                    {"bookmark_ids": [own.id, other.id, missing_id]},
                    status.HTTP_204_NO_CONTENT,
                )
                own.refresh_from_db()
                other.refresh_from_db()
                self.assertEqual(own.is_archived, archived)
                self.assertEqual(other.is_archived, not archived)
                self.assertEqual(other.date_modified, other_modified)

    def test_duplicates_and_repeated_requests_are_safe(self):
        self.authenticate()
        for action, archived in self.actions:
            with self.subTest(action=action):
                bookmark = self.setup_bookmark(is_archived=not archived)
                url = reverse(f"linkding:bookmark-{action}")
                payload = {"bookmark_ids": [bookmark.id, bookmark.id]}
                self.post(url, payload, status.HTTP_204_NO_CONTENT)
                self.post(url, payload, status.HTTP_204_NO_CONTENT)
                bookmark.refresh_from_db()
                self.assertEqual(bookmark.is_archived, archived)

    def test_invalid_payload_does_not_update_any_bookmarks(self):
        self.authenticate()
        for action, archived in self.actions:
            bookmark = self.setup_bookmark(is_archived=not archived)
            original_modified = bookmark.date_modified
            invalid_payloads = [
                {},
                {"bookmark_ids": []},
                {"bookmark_ids": None},
                {"bookmark_ids": str(bookmark.id)},
                {"bookmark_ids": [bookmark.id, "invalid"]},
                {"bookmark_ids": [bookmark.id, 0]},
                {"bookmark_ids": [bookmark.id, -1]},
                {"bookmark_ids": [bookmark.id, 1.5]},
                {"bookmark_ids": [bookmark.id, True]},
                {"bookmark_ids": [bookmark.id, None]},
                {"bookmark_ids": [bookmark.id] * 1001},
            ]
            for payload in invalid_payloads:
                with self.subTest(action=action, payload=payload):
                    self.post(
                        reverse(f"linkding:bookmark-{action}"),
                        payload,
                        status.HTTP_400_BAD_REQUEST,
                    )
                    bookmark.refresh_from_db()
                    self.assertEqual(bookmark.is_archived, not archived)
                    self.assertEqual(bookmark.date_modified, original_modified)

    def test_accepts_maximum_batch_size(self):
        self.authenticate()
        user = self.get_or_create_test_user()
        now = timezone.now()
        for action, archived in self.actions:
            with self.subTest(action=action):
                selected = Bookmark.objects.bulk_create(
                    [
                        Bookmark(
                            owner=user,
                            url=f"https://example.com/{action}/{i}",
                            is_archived=not archived,
                            date_added=now,
                            date_modified=now,
                        )
                        for i in range(1000)
                    ]
                )
                ids = [bookmark.id for bookmark in selected]
                self.post(
                    reverse(f"linkding:bookmark-{action}"),
                    {"bookmark_ids": ids},
                    status.HTTP_204_NO_CONTENT,
                )
                self.assertEqual(
                    Bookmark.objects.filter(id__in=ids, is_archived=archived).count(),
                    1000,
                )

    def test_query_count_does_not_grow_with_batch_size(self):
        self.authenticate()
        GlobalSettings.get()
        for action, archived in self.actions:
            counts = []
            for size in [1, 20]:
                selected = [
                    self.setup_bookmark(is_archived=not archived) for _ in range(size)
                ]
                with CaptureQueriesContext(connection) as queries:
                    self.post(
                        reverse(f"linkding:bookmark-{action}"),
                        {"bookmark_ids": [bookmark.id for bookmark in selected]},
                        status.HTTP_204_NO_CONTENT,
                    )
                counts.append(len(queries))
                updates = [
                    query["sql"]
                    for query in queries
                    if query["sql"].startswith('UPDATE "bookmarks_bookmark"')
                ]
                self.assertEqual(len(updates), 1)
            self.assertEqual(counts[0], counts[1])
