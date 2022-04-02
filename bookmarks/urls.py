from django.conf.urls import url
from django.urls import path, include
from django.views.generic import RedirectView

from bookmarks.api.routes import router
from bookmarks import views

app_name = 'bookmarks'
urlpatterns = [
    # Redirect root to bookmarks index
    url(r'^$', RedirectView.as_view(pattern_name='bookmarks:index', permanent=False)),
    # Bookmarks
    path('bookmarks', views.bookmarks.index, name='index'),
    path('bookmarks/archived', views.bookmarks.archived, name='archived'),
    path('bookmarks/new', views.bookmarks.new, name='new'),
    path('bookmarks/close', views.bookmarks.close, name='close'),
    path('bookmarks/<int:bookmark_id>/edit', views.bookmarks.edit, name='edit'),
    path('bookmarks/action', views.bookmarks.action, name='action'),
    # Settings
    path('settings', views.settings.general, name='settings.index'),
    path('settings/general', views.settings.general, name='settings.general'),
    path('settings/integrations', views.settings.integrations, name='settings.integrations'),
    path('settings/import', views.settings.bookmark_import, name='settings.import'),
    path('settings/export', views.settings.bookmark_export, name='settings.export'),
    # API
    path('api/', include(router.urls), name='api')
]
