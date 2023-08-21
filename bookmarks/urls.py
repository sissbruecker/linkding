from django.urls import path, include
from django.urls import re_path
from django.views.generic import RedirectView

from bookmarks import views
from bookmarks.api.routes import router
from bookmarks.feeds import AllBookmarksFeed, UnreadBookmarksFeed
from bookmarks.views import partials

app_name = 'bookmarks'
urlpatterns = [
    # Redirect root to bookmarks index
    re_path(r'^$', RedirectView.as_view(pattern_name='bookmarks:index', permanent=False)),
    # Bookmarks
    path('bookmarks', views.bookmarks.index, name='index'),
    path('bookmarks/archived', views.bookmarks.archived, name='archived'),
    path('bookmarks/shared', views.bookmarks.shared, name='shared'),
    path('bookmarks/new', views.bookmarks.new, name='new'),
    path('bookmarks/close', views.bookmarks.close, name='close'),
    path('bookmarks/<int:bookmark_id>/edit', views.bookmarks.edit, name='edit'),
    path('bookmarks/action', views.bookmarks.action, name='action'),
    # Partials
    path('bookmarks/partials/bookmark-list/active', partials.active_bookmark_list,
         name='partials.bookmark_list.active'),
    path('bookmarks/partials/tag-cloud/active', partials.active_tag_cloud, name='partials.tag_cloud.active'),
    path('bookmarks/partials/bookmark-list/archived', partials.archived_bookmark_list,
         name='partials.bookmark_list.archived'),
    path('bookmarks/partials/tag-cloud/archived', partials.archived_tag_cloud, name='partials.tag_cloud.archived'),
    # Settings
    path('settings', views.settings.general, name='settings.index'),
    path('settings/general', views.settings.general, name='settings.general'),
    path('settings/integrations', views.settings.integrations, name='settings.integrations'),
    path('settings/import', views.settings.bookmark_import, name='settings.import'),
    path('settings/export', views.settings.bookmark_export, name='settings.export'),
    # Toasts
    path('toasts/acknowledge', views.toasts.acknowledge, name='toasts.acknowledge'),
    # API
    path('api/', include(router.urls), name='api'),
    # Feeds
    path('feeds/<str:feed_key>/all', AllBookmarksFeed(), name='feeds.all'),
    path('feeds/<str:feed_key>/unread', UnreadBookmarksFeed(), name='feeds.unread'),
    # Health check
    path('health', views.health, name='health'),
    # Manifest
    path("manifest.json", views.manifest, name='manifest')
]
