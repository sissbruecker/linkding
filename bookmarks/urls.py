from django.conf.urls import url
from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'bookmarks'
urlpatterns = [
    # Redirect root to bookmarks index
    url(r'^$', RedirectView.as_view(pattern_name='bookmarks:index', permanent=False)),
    path('bookmarks', views.index, name='index'),
    path('bookmarks/new', views.new, name='new'),
    path('bookmarks/<int:bookmark_id>/edit', views.edit, name='edit'),
    # path('bookmarks/<int:bookmark_id>/update', views.update, name='edit'),
    path('bookmarks/<int:bookmark_id>/remove', views.remove, name='remove'),
]
