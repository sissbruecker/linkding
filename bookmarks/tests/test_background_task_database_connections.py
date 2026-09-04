from functools import partial
from unittest import mock

from django.contrib.auth.models import User
from django.db import connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import TransactionTestCase
from huey.contrib.djhuey import HUEY as huey

from bookmarks.models import BookmarkAsset
from bookmarks.services import tasks
from bookmarks.tests.helpers import BookmarkFactoryMixin


def mark_connection_stale():
    """
    Simulate a connection that the database (or network) has dropped on the
    other end while Django still holds on to it. This is what happens in
    deployments where long-lived worker threads keep a connection open across
    long periods of inactivity (e.g. a huey worker against CloudNativePG,
    which drops idle connections). Django's close_old_connections() treats a
    connection as stale when an error occurred since the last commit and
    is_usable() reports the connection as unusable.
    """
    connection = connections["default"]
    assert connection.connection is not None
    # The health check uses this to decide whether the connection can be
    # reused. A real psycopg connection whose socket was closed by the
    # database would fail here.
    connection.is_usable = lambda: False
    connection.errors_occurred = True


class HueyDatabaseConnectionTests(TransactionTestCase, BookmarkFactoryMixin):
    # TransactionTestCase is used because the tests replace the test thread's
    # database connection (the in-memory test database), which cannot happen
    # inside TestCase's transaction wrapper.

    def setUp(self):
        # Execute tasks synchronously in the current thread, like the test
        # suite does for all background task tests.
        huey.immediate = True
        # Touch the database once so the test thread has a connection, the
        # same way a background worker thread does after running a task.
        self.user = self.get_or_create_test_user()
        User.objects.filter(id=self.user.id).exists()

    def tearDown(self):
        huey.immediate = False

    def _recycle_connection_for_test(self):
        # The in-memory test database refuses to be closed (data loss
        # guard), so neutralize the low-level close and use Django's generic
        # close() to let the normal recycle path run: the stale connection is
        # dropped, and a fresh connection is established on the next query.
        connection = connections["default"]
        connection._close = lambda: None
        connection.close = partial(BaseDatabaseWrapper.close, connection)

    def test_postgres_settings_enable_connection_health_checks(self):
        # The postgres branch of the settings must enable CONN_HEALTH_CHECKS
        # and keep connections persistent. Otherwise Django never checks
        # whether a long-lived worker connection is still alive and reusing
        # it fails with "psycopg.OperationalError: the connection is closed".
        import bookmarks.settings.base as base_settings

        original_engine = base_settings.LD_DB_ENGINE
        base_settings.LD_DB_ENGINE = "postgres"
        try:
            database = base_settings.get_default_database()
        finally:
            base_settings.LD_DB_ENGINE = original_engine

        self.assertEqual(
            database["ENGINE"], "django.db.backends.postgresql_psycopg2"
        )
        self.assertTrue(database["CONN_HEALTH_CHECKS"])
        self.assertEqual(database["CONN_MAX_AGE"], None)

    def test_sqlite_settings_unchanged(self):
        # The sqlite branch must stay as it is (persistent connections to
        # counter the ICU memory leak).
        import bookmarks.settings.base as base_settings

        original_engine = base_settings.LD_DB_ENGINE
        base_settings.LD_DB_ENGINE = "sqlite"
        try:
            database = base_settings.get_default_database()
        finally:
            base_settings.LD_DB_ENGINE = original_engine

        self.assertEqual(database["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(database["CONN_MAX_AGE"], None)

    def test_background_tasks_run_close_old_connections_before_running(self):
        # A pre-execute hook must be registered on the huey instance that all
        # background tasks run through, and it must recycle stale database
        # connections before the task runs.
        self.assertTrue(
            huey._pre_execute,
            "A pre-execute hook recycling stale database connections is "
            "expected, so background tasks can re-connect after the database "
            "dropped the idle worker connection.",
        )
        with mock.patch.object(tasks, "close_old_connections") as mock_close:
            tasks._load_web_archive_snapshot_task(bookmark_id=1)

        mock_close.assert_called_once()

    def test_background_task_recycles_stale_connection(self):
        # The periodic snapshot scheduler (the task from the traceback in
        # #1316) queries the database every minute and is therefore the
        # first task to hit the connection that the database dropped while
        # it was idle. It must recycle the connection instead of failing
        # with e.g. psycopg.OperationalError: the connection is closed.
        self._recycle_connection_for_test()

        # Create a pending asset, like create_html_snapshot does.
        bookmark = self.setup_bookmark()
        asset = self.setup_asset(
            bookmark=bookmark,
            asset_type=BookmarkAsset.TYPE_SNAPSHOT,
            status=BookmarkAsset.STATUS_PENDING,
        )
        self.assertTrue(asset.id)

        # Simulate a connection that was dropped by the database.
        mark_connection_stale()
        stale_connection = connections["default"].connection

        with mock.patch("bookmarks.services.assets.create_snapshot") as mock_snapshot:
            tasks._schedule_html_snapshots_task()

        connection = connections["default"]
        self.assertIsNotNone(
            connection.connection, "task should have re-established a connection"
        )
        self.assertIsNot(
            connection.connection,
            stale_connection,
            "the stale connection should have been replaced",
        )
        # The database query that hit the stale connection before the fix
        # must have succeeded on the re-established connection: the task
        # picked up the pending asset again.
        mock_snapshot.assert_called_once_with(asset)

    def test_background_task_does_not_recycle_healthy_connection(self):
        # A connection that still works should not be needlessly closed and
        # re-opened by the task lifecycle. The task performs a real database
        # query, so the connection is in use throughout.
        self.user.profile.enable_favicons = True
        self.user.profile.save()
        connections["default"].cursor().execute("SELECT 1")
        original_connection = connections["default"].connection

        tasks._schedule_bookmarks_without_favicons_task(self.user.id)

        self.assertIs(
            connections["default"].connection,
            original_connection,
            "healthy connections should be reused, not recycled",
        )
