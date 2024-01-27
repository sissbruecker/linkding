from django.apps import AppConfig


class BookmarksConfig(AppConfig):
    name = "bookmarks"

    def ready(self):
        # Register signal handlers
        import bookmarks.signals
