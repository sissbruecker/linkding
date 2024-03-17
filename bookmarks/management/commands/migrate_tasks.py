import json
import os
import sqlite3
import importlib

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Migrate tasks from django-background-tasks to Huey"

    def handle(self, *args, **options):
        db = sqlite3.connect(os.path.join("data", "db.sqlite3"))

        # Check if background_task table exists
        cursor = db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='background_task'"
        )
        row = cursor.fetchone()
        if not row:
            self.stdout.write(
                "Legacy task table does not exist. Skipping task migration"
            )
            return

        # Load legacy tasks
        cursor.execute("SELECT id, task_name, task_params FROM background_task")
        legacy_tasks = cursor.fetchall()

        if len(legacy_tasks) == 0:
            self.stdout.write("No legacy tasks found. Skipping task migration")
            return

        self.stdout.write(
            f"Found {len(legacy_tasks)} legacy tasks. Migrating to Huey..."
        )

        # Migrate tasks to Huey
        succeeded_tasks = []
        for task in legacy_tasks:
            task_id = task[0]
            task_name = task[1]
            task_params_json = task[2]
            try:
                task_params = json.loads(task_params_json)
                function_params = task_params[0]

                # Resolve task function
                module_name, func_name = task_name.rsplit(".", 1)
                module = importlib.import_module(module_name)
                func = getattr(module, func_name)

                # Call task function
                func(*function_params)
                succeeded_tasks.append(task_id)
            except Exception:
                self.stderr.write(f"Error migrating task [{task_id}] {task_name}")

        self.stdout.write(f"Migrated {len(succeeded_tasks)} tasks successfully")

        # Clean up
        try:
            placeholders = ", ".join("?" for _ in succeeded_tasks)
            sql = f"DELETE FROM background_task WHERE id IN ({placeholders})"
            cursor.execute(sql, succeeded_tasks)
            db.commit()
            self.stdout.write(
                f"Deleted {len(succeeded_tasks)} migrated tasks from legacy table"
            )
        except Exception:
            self.stderr.write("Error cleaning up legacy tasks")

        cursor.close()
        db.close()
