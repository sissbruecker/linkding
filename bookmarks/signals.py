import hashlib

from django.conf import settings
from django.db.backends.signals import connection_created
from django.dispatch import receiver


def _sqlite_md5(value):
    if value is None:
        return None
    return hashlib.md5(str(value).encode()).hexdigest()


@receiver(connection_created)
def extend_sqlite(connection=None, **kwargs):
    if connection.vendor != "sqlite":
        return

    # Register md5 so random-sort ordering is identical across engines
    # (Postgres ships md5 natively).
    connection.connection.create_function("md5", 1, _sqlite_md5, deterministic=True)

    # Load ICU extension into Sqlite connection to support case-insensitive
    # comparisons with unicode characters
    if settings.USE_SQLITE_ICU_EXTENSION:
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
