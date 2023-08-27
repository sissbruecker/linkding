from os import path

from django.contrib.auth import user_logged_in
from django.db.backends.signals import connection_created
from django.dispatch import receiver

from bookmarks.services import tasks

icu_extension_path = './libicu.so'
icu_extension_exists = path.exists(icu_extension_path)


@receiver(user_logged_in)
def user_logged_in(sender, request, user, **kwargs):
    tasks.schedule_bookmarks_without_snapshots(user)


@receiver(connection_created)
def extend_sqlite(connection=None, **kwargs):
    # Load ICU extension into Sqlite connection to support case-insensitive
    # comparisons with unicode characters
    if connection.vendor == 'sqlite' and icu_extension_exists:
        connection.connection.enable_load_extension(True)
        connection.connection.load_extension('./libicu')

        with connection.cursor() as cursor:
            # Load an ICU collation for case-insensitive ordering.
            # The first param can be a specific locale, it seems that not
            # providing one will use a default collation from the ICU project
            # that works reasonably for multiple languages
            cursor.execute("SELECT icu_load_collation('', 'ICU');")
