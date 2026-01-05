from django.conf import settings
from django.contrib.auth import views as django_auth_views
from django.urls import include, path, re_path

from bookmarks import feeds
from bookmarks.admin import linkding_admin_site
from bookmarks.api import routes as api_routes
from bookmarks.views import assets as assets_views
from bookmarks.views import auth as linkding_auth_views
from bookmarks.views import bookmarks as bookmarks_views
from bookmarks.views import bundles as bundles_views
from bookmarks.views import settings as settings_views
from bookmarks.views import tags as tags_views
from bookmarks.views import toasts as toasts_views
from bookmarks.views.custom_css import custom_css as custom_css_view
from bookmarks.views.health import health as health_view
from bookmarks.views.manifest import manifest as manifest_view
from bookmarks.views.opensearch import opensearch as opensearch_view
from bookmarks.views.root import root as root_view

urlpatterns = [
    # Root view handling redirection based on user authentication
    re_path(r"^$", root_view, name="root"),
    # Bookmarks
    path("bookmarks", bookmarks_views.index, name="bookmarks.index"),
    path(
        "bookmarks/action", bookmarks_views.index_action, name="bookmarks.index.action"
    ),
    path("bookmarks/archived", bookmarks_views.archived, name="bookmarks.archived"),
    path(
        "bookmarks/archived/action",
        bookmarks_views.archived_action,
        name="bookmarks.archived.action",
    ),
    path("bookmarks/shared", bookmarks_views.shared, name="bookmarks.shared"),
    path(
        "bookmarks/shared/action",
        bookmarks_views.shared_action,
        name="bookmarks.shared.action",
    ),
    path("bookmarks/new", bookmarks_views.new, name="bookmarks.new"),
    path("bookmarks/close", bookmarks_views.close, name="bookmarks.close"),
    path(
        "bookmarks/<int:bookmark_id>/edit", bookmarks_views.edit, name="bookmarks.edit"
    ),
    # Assets
    path(
        "assets/<int:asset_id>",
        assets_views.view,
        name="assets.view",
    ),
    path(
        "assets/<int:asset_id>/read",
        assets_views.read,
        name="assets.read",
    ),
    # Bundles
    path("bundles", bundles_views.index, name="bundles.index"),
    path("bundles/action", bundles_views.action, name="bundles.action"),
    path("bundles/new", bundles_views.new, name="bundles.new"),
    path("bundles/<int:bundle_id>/edit", bundles_views.edit, name="bundles.edit"),
    path("bundles/preview", bundles_views.preview, name="bundles.preview"),
    # Tags
    path("tags", tags_views.tags_index, name="tags.index"),
    path("tags/new", tags_views.tag_new, name="tags.new"),
    path("tags/<int:tag_id>/edit", tags_views.tag_edit, name="tags.edit"),
    path("tags/merge", tags_views.tag_merge, name="tags.merge"),
    # Settings
    path("settings", settings_views.general, name="settings.index"),
    path("settings/general", settings_views.general, name="settings.general"),
    path("settings/update", settings_views.update, name="settings.update"),
    path(
        "settings/integrations",
        settings_views.integrations,
        name="settings.integrations",
    ),
    path(
        "settings/integrations/create-api-token",
        settings_views.create_api_token,
        name="settings.integrations.create_api_token",
    ),
    path(
        "settings/integrations/delete-api-token",
        settings_views.delete_api_token,
        name="settings.integrations.delete_api_token",
    ),
    path("settings/import", settings_views.bookmark_import, name="settings.import"),
    path("settings/export", settings_views.bookmark_export, name="settings.export"),
    # Toasts
    path("toasts/acknowledge", toasts_views.acknowledge, name="toasts.acknowledge"),
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
    path("health", health_view, name="health"),
    # Manifest
    path("manifest.json", manifest_view, name="manifest"),
    # Custom CSS
    path("custom_css", custom_css_view, name="custom_css"),
    # OpenSearch
    path("opensearch.xml", opensearch_view, name="opensearch"),
]

# Live reload (debug only)
if settings.DEBUG:
    from bookmarks.views import reload

    urlpatterns.append(path("live_reload", reload.live_reload, name="live_reload"))

# Put all linkding URLs into a linkding namespace
urlpatterns = [path("", include((urlpatterns, "linkding")))]

# Auth
urlpatterns += [
    path(
        "login/",
        linkding_auth_views.LinkdingLoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", django_auth_views.LogoutView.as_view(), name="logout"),
    path(
        "change-password/",
        linkding_auth_views.LinkdingPasswordChangeView.as_view(),
        name="change_password",
    ),
    path(
        "password-change-done/",
        django_auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
]

# Admin
urlpatterns.append(path("admin/", linkding_admin_site.urls))

# OIDC
if settings.LD_ENABLE_OIDC:
    urlpatterns.append(path("oidc/", include("mozilla_django_oidc.urls")))

# Debug toolbar
# if settings.DEBUG:
#    import debug_toolbar
#    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))

# Context path
if settings.LD_CONTEXT_PATH:
    urlpatterns = [path(settings.LD_CONTEXT_PATH, include(urlpatterns))]
