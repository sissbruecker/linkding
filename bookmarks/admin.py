from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, QuerySet
from django.utils.translation import ngettext, gettext
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import Token

from bookmarks.models import Bookmark, Tag
from bookmarks.services.bookmarks import archive_bookmark, unarchive_bookmark


class LinkdingAdminSite(AdminSite):
    site_header = 'linkding administration'
    site_title = 'linkding Admin'


class AdminBookmark(admin.ModelAdmin):
    list_display = ('resolved_title', 'url', 'is_archived', 'owner', 'date_added')
    search_fields = ('title', 'description', 'website_title', 'website_description', 'url', 'tags__name')
    list_filter = ('owner__username', 'is_archived', 'tags',)
    ordering = ('-date_added',)
    actions = ['archive_selected_bookmarks', 'unarchive_selected_bookmarks']

    def archive_selected_bookmarks(self, request, queryset: QuerySet):
        for bookmark in queryset:
            archive_bookmark(bookmark)
        bookmarks_count = queryset.count()
        self.message_user(request, ngettext(
            '%d bookmark was successfully archived.',
            '%d bookmarks were successfully archived.',
            bookmarks_count,
        ) % bookmarks_count, messages.SUCCESS)

    def unarchive_selected_bookmarks(self, request, queryset: QuerySet):
        for bookmark in queryset:
            unarchive_bookmark(bookmark)
        bookmarks_count = queryset.count()
        self.message_user(request, ngettext(
            '%d bookmark was successfully unarchived.',
            '%d bookmarks were successfully unarchived.',
            bookmarks_count,
        ) % bookmarks_count, messages.SUCCESS)


class AdminTag(admin.ModelAdmin):
    list_display = ('name', 'bookmarks_count', 'owner', 'date_added')
    search_fields = ('name', 'owner__username')
    list_filter = ('owner__username',)
    ordering = ('-date_added',)
    actions = ['delete_unused_tags']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(bookmarks_count=Count("bookmark"))
        return queryset

    def bookmarks_count(self, obj):
        return obj.bookmarks_count

    def delete_unused_tags(self, request, queryset: QuerySet):
        unused_tags = queryset.filter(bookmark__isnull=True)
        unused_tags_count = unused_tags.count()
        for tag in unused_tags:
            tag.delete()

        if unused_tags_count > 0:
            self.message_user(request, ngettext(
                '%d unused tag was successfully deleted.',
                '%d unused tags were successfully deleted.',
                unused_tags_count,
            ) % unused_tags_count, messages.SUCCESS)
        else:
            self.message_user(request, gettext(
                'There were no unused tags in the selection',
            ), messages.SUCCESS)


linkding_admin_site = LinkdingAdminSite()
linkding_admin_site.register(Bookmark, AdminBookmark)
linkding_admin_site.register(Tag, AdminTag)
linkding_admin_site.register(User, UserAdmin)
linkding_admin_site.register(Token, TokenAdmin)
