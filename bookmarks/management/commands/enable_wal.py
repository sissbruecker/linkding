import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Determine journal mode when using an SQLite database"

    # https://www.sqlite.org/pragma.html#pragma_journal_mode
    parser.add_argument("--journal-mode", default="wal", help="Pick sqlite journaling mode")

    def handle(self, *args, **options):
        if not settings.USE_SQLITE:
            return

        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA journal_mode={options['journal-mode']}")
            current_mode = cursor.fetchone()[0]
            logger.info(f"Journal mode: {current_mode}")
