from django.urls import path

from . import views

app_name = 'bookmarks'
urlpatterns = [
    path('', views.index, name='index'),
    path('bookmark/<int:bookmark_id>', views.detail, name='detail'),
    path('bookmark/<int:bookmark_id>/remove', views.remove, name='remove'),
]
