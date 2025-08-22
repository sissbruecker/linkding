from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.urls import re_path
from django.conf import settings

from bookmarks import feeds, views
from bookmarks.admin import linkding_admin_site
from bookmarks.api import routes as api_routes

urlpatterns = [
    # Root view handling redirection based on user authentication
    re_path(r"^$", views.root, name="root"),
    # Bookmarks
    path("bookmarks", views.bookmarks.index, name="bookmarks.index"),
    path(
        "bookmarks/action", views.bookmarks.index_action, name="bookmarks.index.action"
    ),
    path("bookmarks/archived", views.bookmarks.archived, name="bookmarks.archived"),
    path(
        "bookmarks/archived/action",
        views.bookmarks.archived_action,
        name="bookmarks.archived.action",
    ),
    path("bookmarks/shared", views.bookmarks.shared, name="bookmarks.shared"),
    path(
        "bookmarks/shared/action",
        views.bookmarks.shared_action,
        name="bookmarks.shared.action",
    ),
    path("bookmarks/new", views.bookmarks.new, name="bookmarks.new"),
    path("bookmarks/close", views.bookmarks.close, name="bookmarks.close"),
    path(
        "bookmarks/<int:bookmark_id>/edit", views.bookmarks.edit, name="bookmarks.edit"
    ),
    path(
        "bookmarks/<int:bookmark_id>/visit", views.bookmarks.visit, name="bookmarks.visit"
    ),
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
    # Bundles
    path("bundles", views.bundles.index, name="bundles.index"),
    path("bundles/action", views.bundles.action, name="bundles.action"),
    path("bundles/new", views.bundles.new, name="bundles.new"),
    path("bundles/<int:bundle_id>/edit", views.bundles.edit, name="bundles.edit"),
    path("bundles/preview", views.bundles.preview, name="bundles.preview"),
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
    path("api/", include(api_routes.default_router.urls)),
    path("api/bookmarks/", include(api_routes.bookmark_router.urls)),
    path(
        "api/bookmarks/<int:bookmark_id>/assets/",
        include(api_routes.bookmark_asset_router.urls),
    ),
    path("api/tags/", include(api_routes.tag_router.urls)),
    path("api/bundles/", include(api_routes.bundle_router.urls)),
    path("api/user/", include(api_routes.user_router.urls)),
    # Feeds
    path("feeds/<str:feed_key>/all", feeds.AllBookmarksFeed(), name="feeds.all"),
    path(
        "feeds/<str:feed_key>/unread", feeds.UnreadBookmarksFeed(), name="feeds.unread"
    ),
    path(
        "feeds/<str:feed_key>/shared", feeds.SharedBookmarksFeed(), name="feeds.shared"
    ),
    path("feeds/shared", feeds.PublicSharedBookmarksFeed(), name="feeds.public_shared"),
    # Health check
    path("health", views.health, name="health"),
    # Manifest
    path("manifest.json", views.manifest, name="manifest"),
    # Custom CSS
    path("custom_css", views.custom_css, name="custom_css"),
    # OpenSearch
    path("opensearch.xml", views.opensearch, name="opensearch"),
]

# Put all linkding URLs into a linkding namespace
urlpatterns = [path("", include((urlpatterns, "linkding")))]

# Auth
urlpatterns += [
    path(
        "login/",
        views.auth.LinkdingLoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "change-password/",
        views.auth.LinkdingPasswordChangeView.as_view(),
        name="change_password",
    ),
    path(
        "password-change-done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
]

# Admin
urlpatterns.append(path("admin/", linkding_admin_site.urls))

# OIDC
if settings.LD_ENABLE_OIDC:
    urlpatterns.append(path("oidc/", include("mozilla_django_oidc.urls")))

# Debug toolbar
if settings.DEBUG:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))

# Registration
if settings.ALLOW_REGISTRATION:
    urlpatterns.append(path("", include("django_registration.backends.one_step.urls")))

# Context path
if settings.LD_CONTEXT_PATH:
    urlpatterns = [path(settings.LD_CONTEXT_PATH, include(urlpatterns))]
