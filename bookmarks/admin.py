from django.contrib import admin

# Register your models here.
from bookmarks.models import Bookmark

admin.site.register(Bookmark)
