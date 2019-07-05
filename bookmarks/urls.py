from django.conf.urls import url
from django.urls import path
from django.views.generic import RedirectView

from bookmarks import views

app_name = 'bookmarks'
urlpatterns = [
    # Redirect root to bookmarks index
    url(r'^$', RedirectView.as_view(pattern_name='bookmarks:index', permanent=False)),
    # Bookmarks
    path('bookmarks', views.bookmarks_index, name='index'),
    path('bookmarks/new', views.bookmarks_new, name='new'),
    path('bookmarks/close', views.bookmarks_close, name='close'),
    path('bookmarks/<int:bookmark_id>/edit', views.bookmarks_edit, name='edit'),
    path('bookmarks/<int:bookmark_id>/remove', views.bookmarks_remove, name='remove'),
    path('bookmarklet', views.bookmarks_bookmarklet, name='bookmarklet'),
    # Settings
    path('settings', views.settings_index, name='settings_index'),
    path('settings/import', views.settings_bookmark_import, name='settings_import'),
    # API
    path('api/website_metadata', views.api.api_website_metadata, name='api.website_metadata'),
]
