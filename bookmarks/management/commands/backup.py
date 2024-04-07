import sqlite3
import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates a backup of the linkding database"

    def add_arguments(self, parser):
        parser.add_argument("destination", type=str, help="Backup file destination")

    def handle(self, *args, **options):
        destination = options["destination"]

        def progress(status, remaining, total):
            self.stdout.write(f"Copied {total-remaining} of {total} pages...")

        source_db = sqlite3.connect(os.path.join("data", "db.sqlite3"))
        backup_db = sqlite3.connect(destination)
        with backup_db:
            source_db.backup(backup_db, pages=50, progress=progress)
        backup_db.close()
        source_db.close()

        self.stdout.write(self.style.SUCCESS(f"Backup created at {destination}"))
        self.stdout.write(
            self.style.WARNING(
                "This backup method is deprecated and may be removed in the future. Please use the full_backup command instead, which creates backup zip file with all contents of the data folder."
            )
        )
