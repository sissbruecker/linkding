import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Enable WAL journal mode when using an SQLite database"

    def handle(self, *args, **options):
        if not settings.USE_SQLITE:
            return

        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode")
            current_mode = cursor.fetchone()[0]
            logger.info(f"Current journal mode: {current_mode}")
            if current_mode != "wal":
                cursor.execute("PRAGMA journal_mode=wal;")
                logger.info("Switched to WAL journal mode")
