from background_task.models import Task, CompletedTask
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Remove task locks and clear completed task history"

    def handle(self, *args, **options):
        # Remove task locks
        # If the background task processor exited while executing tasks, these tasks would still be marked as locked,
        # even though no process is working on them, and would prevent the task processor from picking the next task in
        # the queue
        Task.objects.all().update(locked_by=None, locked_at=None)
        # Clear task history to prevent them from bloating the DB
        CompletedTask.objects.all().delete()
