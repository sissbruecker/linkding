from django.conf import settings
from django.contrib.auth import user_logged_in
from django.db.backends.signals import connection_created
from django.dispatch import receiver

from bookmarks.services import tasks


@receiver(user_logged_in)
def user_logged_in(sender, request, user, **kwargs):
    tasks.schedule_bookmarks_without_snapshots(user)


@receiver(connection_created)
def extend_sqlite(connection=None, **kwargs):
    # Load ICU extension into Sqlite connection to support case-insensitive
    # comparisons with unicode characters
    if connection.vendor == "sqlite" and settings.USE_SQLITE_ICU_EXTENSION:
        connection.connection.enable_load_extension(True)
        connection.connection.load_extension(
            settings.SQLITE_ICU_EXTENSION_PATH.rstrip(".so")
        )

        with connection.cursor() as cursor:
            # Load an ICU collation for case-insensitive ordering.
            # The first param can be a specific locale, it seems that not
            # providing one will use a default collation from the ICU project
            # that works reasonably for multiple languages
            cursor.execute("SELECT icu_load_collation('', 'ICU');")
