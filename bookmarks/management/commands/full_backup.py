import sqlite3
import os
import tempfile
import zipfile

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates a backup of the linkding data folder"

    def add_arguments(self, parser):
        parser.add_argument("backup_file", type=str, help="Backup zip file destination")

    def handle(self, *args, **options):
        backup_file = options["backup_file"]
        with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Backup the database
            self.stdout.write("Create database backup...")
            with tempfile.TemporaryDirectory() as temp_dir:
                backup_db_file = os.path.join(temp_dir, "db.sqlite3")
                self.backup_database(backup_db_file)
                zip_file.write(backup_db_file, "db.sqlite3")

            # Backup the assets folder
            if not os.path.exists(os.path.join("data", "assets")):
                self.stdout.write(
                    self.style.WARNING("No assets folder found. Skipping...")
                )
            else:
                self.stdout.write("Backup bookmark assets...")
                assets_folder = os.path.join("data", "assets")
                for root, _, files in os.walk(assets_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zip_file.write(file_path, os.path.join("assets", file))

            # Backup the favicons folder
            if not os.path.exists(os.path.join("data", "favicons")):
                self.stdout.write(
                    self.style.WARNING("No favicons folder found. Skipping...")
                )
            else:
                self.stdout.write("Backup bookmark favicons...")
                favicons_folder = os.path.join("data", "favicons")
                for root, _, files in os.walk(favicons_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zip_file.write(file_path, os.path.join("favicons", file))

            # Backup the previews folder
            if not os.path.exists(os.path.join("data", "previews")):
                self.stdout.write(
                    self.style.WARNING("No previews folder found. Skipping...")
                )
            else:
                self.stdout.write("Backup bookmark previews...")
                previews_folder = os.path.join("data", "previews")
                for root, _, files in os.walk(previews_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zip_file.write(file_path, os.path.join("previews", file))

        self.stdout.write(self.style.SUCCESS(f"Backup created at {backup_file}"))

    def backup_database(self, backup_db_file):
        def progress(status, remaining, total):
            self.stdout.write(f"Copied {total-remaining} of {total} pages...")

        source_db = sqlite3.connect(os.path.join("data", "db.sqlite3"))
        backup_db = sqlite3.connect(backup_db_file)
        with backup_db:
            source_db.backup(backup_db, pages=50, progress=progress)
        backup_db.close()
        source_db.close()
