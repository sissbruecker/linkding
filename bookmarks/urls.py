from django.urls import path, include
from django.urls import re_path
from django.views.generic import RedirectView

from bookmarks import views
from bookmarks.api.routes import router
from bookmarks.feeds import (
    AllBookmarksFeed,
    UnreadBookmarksFeed,
    SharedBookmarksFeed,
    PublicSharedBookmarksFeed,
)
from bookmarks.views import partials

app_name = "bookmarks"
urlpatterns = [
    # Redirect root to bookmarks index
    re_path(
        r"^$", RedirectView.as_view(pattern_name="bookmarks:index", permanent=False)
    ),
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
    path(
        "bookmarks/<int:bookmark_id>/details",
        views.bookmarks.details,
        name="details",
    ),
    path(
        "bookmarks/<int:bookmark_id>/details_modal",
        views.bookmarks.details_modal,
        name="details_modal",
    ),
    path(
        "bookmarks/<int:bookmark_id>/details_assets",
        views.bookmarks.details_assets,
        name="details_assets",
    ),
    # Assets
    path(
        "assets/<int:asset_id>",
        views.assets.view,
        name="assets.view",
    ),
    # Partials
    path(
        "bookmarks/partials/bookmark-list/active",
        partials.active_bookmark_list,
        name="partials.bookmark_list.active",
    ),
    path(
        "bookmarks/partials/tag-cloud/active",
        partials.active_tag_cloud,
        name="partials.tag_cloud.active",
    ),
    path(
        "bookmarks/partials/tag-modal/active",
        partials.active_tag_modal,
        name="partials.tag_modal.active",
    ),
    path(
        "bookmarks/partials/bookmark-list/archived",
        partials.archived_bookmark_list,
        name="partials.bookmark_list.archived",
    ),
    path(
        "bookmarks/partials/tag-cloud/archived",
        partials.archived_tag_cloud,
        name="partials.tag_cloud.archived",
    ),
    path(
        "bookmarks/partials/tag-modal/archived",
        partials.archived_tag_modal,
        name="partials.tag_modal.archived",
    ),
    path(
        "bookmarks/partials/bookmark-list/shared",
        partials.shared_bookmark_list,
        name="partials.bookmark_list.shared",
    ),
    path(
        "bookmarks/partials/tag-cloud/shared",
        partials.shared_tag_cloud,
        name="partials.tag_cloud.shared",
    ),
    path(
        "bookmarks/partials/tag-modal/shared",
        partials.shared_tag_modal,
        name="partials.tag_modal.shared",
    ),
    # Settings
    path("settings", views.settings.general, name="settings.index"),
    path("settings/general", views.settings.general, name="settings.general"),
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
]
