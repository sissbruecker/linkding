from background_task.admin import TaskAdmin, CompletedTaskAdmin
from background_task.models import Task, CompletedTask
from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, QuerySet
from django.utils.translation import ngettext, gettext
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import TokenProxy

from bookmarks.models import Bookmark, Tag, UserProfile, Toast, FeedToken
from bookmarks.services.bookmarks import archive_bookmark, unarchive_bookmark


class LinkdingAdminSite(AdminSite):
    site_header = 'linkding administration'
    site_title = 'linkding Admin'


class AdminBookmark(admin.ModelAdmin):
    list_display = ('resolved_title', 'url', 'is_archived', 'owner', 'date_added')
    search_fields = ('title', 'description', 'website_title', 'website_description', 'url', 'tags__name')
    list_filter = ('owner__username', 'is_archived', 'unread', 'tags',)
    ordering = ('-date_added',)
    actions = ['delete_selected_bookmarks', 'archive_selected_bookmarks', 'unarchive_selected_bookmarks', 'mark_as_read', 'mark_as_unread']

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Remove default delete action, which gets replaced by delete_selected_bookmarks below
        # The default action shows a confirmation page which can fail in production when selecting all bookmarks and the
        # number of objects to delete exceeds the value in DATA_UPLOAD_MAX_NUMBER_FIELDS (1000 by default)
        del actions['delete_selected']
        return actions

    def delete_selected_bookmarks(self, request, queryset: QuerySet):
        bookmarks_count = queryset.count()
        for bookmark in queryset:
            bookmark.delete()
        self.message_user(request, ngettext(
            '%d bookmark was successfully deleted.',
            '%d bookmarks were successfully deleted.',
            bookmarks_count,
        ) % bookmarks_count, messages.SUCCESS)

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

    def mark_as_read(self, request, queryset: QuerySet):
        bookmarks_count = queryset.count()
        queryset.update(unread=False)
        self.message_user(request, ngettext(
            '%d bookmark marked as read.',
            '%d bookmarks marked as read.',
            bookmarks_count,
        ) % bookmarks_count, messages.SUCCESS)

    def mark_as_unread(self, request, queryset: QuerySet):
        bookmarks_count = queryset.count()
        queryset.update(unread=True)
        self.message_user(request, ngettext(
            '%d bookmark marked as unread.',
            '%d bookmarks marked as unread.',
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

    bookmarks_count.admin_order_field = 'bookmarks_count'

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


class AdminUserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    readonly_fields = ('search_preferences', )

class AdminCustomUser(UserAdmin):
    inlines = (AdminUserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(AdminCustomUser, self).get_inline_instances(request, obj)


class AdminToast(admin.ModelAdmin):
    list_display = ('key', 'message', 'owner', 'acknowledged')
    search_fields = ('key', 'message')
    list_filter = ('owner__username',)


class AdminFeedToken(admin.ModelAdmin):
    list_display = ('key', 'user')
    search_fields = ['key']
    list_filter = ('user__username',)


linkding_admin_site = LinkdingAdminSite()
linkding_admin_site.register(Bookmark, AdminBookmark)
linkding_admin_site.register(Tag, AdminTag)
linkding_admin_site.register(User, AdminCustomUser)
linkding_admin_site.register(TokenProxy, TokenAdmin)
linkding_admin_site.register(Toast, AdminToast)
linkding_admin_site.register(FeedToken, AdminFeedToken)
linkding_admin_site.register(Task, TaskAdmin)
linkding_admin_site.register(CompletedTask, CompletedTaskAdmin)
