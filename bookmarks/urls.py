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
    path('bookmarks/new', views.bookmarks.new, name='new'),
    path('bookmarks/close', views.bookmarks.close, name='close'),
    path('bookmarks/<int:bookmark_id>/edit', views.bookmarks.edit, name='edit'),
    path('bookmarks/<int:bookmark_id>/remove', views.bookmarks.remove, name='remove'),
    path('bookmarklet', views.bookmarks.bookmarklet, name='bookmarklet'),
    # Settings
    path('settings', views.settings.index, name='settings.index'),
    path('settings/import', views.settings.bookmark_import, name='settings.import'),
    path('settings/export', views.settings.bookmark_export, name='settings.export'),
    # API
    path('api/check_url', views.api.check_url, name='api.check_url'),
    url(r'^api/', include(router.urls))
]
