from django.contrib import admin

from bookmarks.models import Bookmark, Tag

@admin.register(Bookmark)
class AdminBookmark(admin.ModelAdmin):
  list_display = ('title', 'url', 'date_added')
  search_fields = ('title', 'url', 'tags__name')
  list_filter = ('tags',)
  ordering = ('-date_added', )

@admin.register(Tag)
class AdminTag(admin.ModelAdmin):
  list_display = ('name', 'date_added', 'owner')
  search_fields = ('name', 'owner__username')
  list_filter = ('owner__username', )
  ordering = ('-date_added', )
