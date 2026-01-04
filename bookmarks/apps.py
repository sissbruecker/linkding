from django.apps import AppConfig


class BookmarksConfig(AppConfig):
    name = "bookmarks"

    def ready(self):
        # Register signal handlers
        # noinspection PyUnusedImports
        import bookmarks.signals  # noqa: F401
