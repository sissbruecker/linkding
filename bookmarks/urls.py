from django.urls import path, include
from django.urls import re_path

from bookmarks import views
from bookmarks.api.routes import router
from bookmarks.feeds import (
    AllBookmarksFeed,
    UnreadBookmarksFeed,
    SharedBookmarksFeed,
    PublicSharedBookmarksFeed,
)

app_name = "bookmarks"
urlpatterns = [
    # Root view handling redirection based on user authentication
    re_path(r"^$", views.root, name="root"),
    # Bookmarks
    path("bookmarks", views.bookmarks.index, name="index"),
    path("bookmarks/action", views.bookmarks.index_action, name="index.action"),
    path("bookmarks/archived", views.bookmarks.archived, name="archived"),
    path(
        "bookmarks/archived/action",
        views.bookmarks.archived_action,
        name="archived.action",
    ),
    path("bookmarks/shared", views.bookmarks.shared, name="shared"),
    path(
        "bookmarks/shared/action", views.bookmarks.shared_action, name="shared.action"
    ),
    path("bookmarks/new", views.bookmarks.new, name="new"),
    path("bookmarks/close", views.bookmarks.close, name="close"),
    path("bookmarks/<int:bookmark_id>/edit", views.bookmarks.edit, name="edit"),
    # Assets
    path(
        "assets/<int:asset_id>",
        views.assets.view,
        name="assets.view",
    ),
    path(
        "assets/<int:asset_id>/read",
        views.assets.read,
        name="assets.read",
    ),
    # Settings
    path("settings", views.settings.general, name="settings.index"),
    path("settings/general", views.settings.general, name="settings.general"),
    path("settings/update", views.settings.update, name="settings.update"),
    path(
        "settings/integrations",
        views.settings.integrations,
        name="settings.integrations",
    ),
    path("settings/import", views.settings.bookmark_import, name="settings.import"),
    path("settings/export", views.settings.bookmark_export, name="settings.export"),
    # Toasts
    path("toasts/acknowledge", views.toasts.acknowledge, name="toasts.acknowledge"),
    # API
    path("api/", include(router.urls), name="api"),
    # Feeds
    path("feeds/<str:feed_key>/all", AllBookmarksFeed(), name="feeds.all"),
    path("feeds/<str:feed_key>/unread", UnreadBookmarksFeed(), name="feeds.unread"),
    path("feeds/<str:feed_key>/shared", SharedBookmarksFeed(), name="feeds.shared"),
    path("feeds/shared", PublicSharedBookmarksFeed(), name="feeds.public_shared"),
    # Health check
    path("health", views.health, name="health"),
    # Manifest
    path("manifest.json", views.manifest, name="manifest"),
    # Custom CSS
    path("custom_css", views.custom_css, name="custom_css"),
]
