from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, QuerySet
from django.shortcuts import render
from django.urls import path
from django.utils.translation import ngettext, gettext
from huey.contrib.djhuey import HUEY as huey
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import TokenProxy

from bookmarks.models import Bookmark, BookmarkAsset, Tag, UserProfile, Toast, FeedToken
from bookmarks.services.bookmarks import archive_bookmark, unarchive_bookmark


# Custom paginator to paginate through Huey tasks
class TaskPaginator(Paginator):
    def __init__(self):
        super().__init__(self, 100)
        self.task_count = huey.storage.queue_size()

    @property
    def count(self):
        return self.task_count

    def page(self, number):
        limit = self.per_page
        offset = (number - 1) * self.per_page
        return self._get_page(
            self.enqueued_items(limit, offset),
            number,
            self,
        )

    # Copied from Huey's SqliteStorage with some modifications to allow pagination
    def enqueued_items(self, limit, offset):
        to_bytes = lambda b: bytes(b) if not isinstance(b, bytes) else b
        sql = "select data from task where queue=? order by priority desc, id limit ? offset ?"
        params = (huey.storage.name, limit, offset)

        serialized_tasks = [
            to_bytes(i) for i, in huey.storage.sql(sql, params, results=True)
        ]
        return [huey.deserialize_task(task) for task in serialized_tasks]


# Custom view to display Huey tasks in the admin
def background_task_view(request):
    page_number = int(request.GET.get("p", 1))
    paginator = TaskPaginator()
    page = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_number, on_each_side=2, on_ends=2)
    context = {
        **linkding_admin_site.each_context(request),
        "title": "Background tasks",
        "page": page,
        "page_range": page_range,
        "tasks": page.object_list,
    }
    return render(request, "admin/background_tasks.html", context)


class LinkdingAdminSite(AdminSite):
    site_header = "linkding administration"
    site_title = "linkding Admin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("tasks/", background_task_view, name="background_tasks"),
        ]
        return custom_urls + urls

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        app_list += [
            {
                "name": "Huey",
                "app_label": "huey_app",
                "models": [
                    {
                        "name": "Queued tasks",
                        "object_name": "background_tasks",
                        "admin_url": "/admin/tasks/",
                        "view_only": True,
                    }
                ],
            }
        ]
        return app_list


class AdminBookmark(admin.ModelAdmin):
    list_display = ("resolved_title", "url", "is_archived", "owner", "date_added")
    search_fields = (
        "title",
        "description",
        "website_title",
        "website_description",
        "url",
        "tags__name",
    )
    list_filter = (
        "owner__username",
        "is_archived",
        "unread",
        "tags",
    )
    ordering = ("-date_added",)
    actions = [
        "delete_selected_bookmarks",
        "archive_selected_bookmarks",
        "unarchive_selected_bookmarks",
        "mark_as_read",
        "mark_as_unread",
    ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Remove default delete action, which gets replaced by delete_selected_bookmarks below
        # The default action shows a confirmation page which can fail in production when selecting all bookmarks and the
        # number of objects to delete exceeds the value in DATA_UPLOAD_MAX_NUMBER_FIELDS (1000 by default)
        del actions["delete_selected"]
        return actions

    def delete_selected_bookmarks(self, request, queryset: QuerySet):
        bookmarks_count = queryset.count()
        for bookmark in queryset:
            bookmark.delete()
        self.message_user(
            request,
            ngettext(
                "%d bookmark was successfully deleted.",
                "%d bookmarks were successfully deleted.",
                bookmarks_count,
            )
            % bookmarks_count,
            messages.SUCCESS,
        )

    def archive_selected_bookmarks(self, request, queryset: QuerySet):
        for bookmark in queryset:
            archive_bookmark(bookmark)
        bookmarks_count = queryset.count()
        self.message_user(
            request,
            ngettext(
                "%d bookmark was successfully archived.",
                "%d bookmarks were successfully archived.",
                bookmarks_count,
            )
            % bookmarks_count,
            messages.SUCCESS,
        )

    def unarchive_selected_bookmarks(self, request, queryset: QuerySet):
        for bookmark in queryset:
            unarchive_bookmark(bookmark)
        bookmarks_count = queryset.count()
        self.message_user(
            request,
            ngettext(
                "%d bookmark was successfully unarchived.",
                "%d bookmarks were successfully unarchived.",
                bookmarks_count,
            )
            % bookmarks_count,
            messages.SUCCESS,
        )

    def mark_as_read(self, request, queryset: QuerySet):
        bookmarks_count = queryset.count()
        queryset.update(unread=False)
        self.message_user(
            request,
            ngettext(
                "%d bookmark marked as read.",
                "%d bookmarks marked as read.",
                bookmarks_count,
            )
            % bookmarks_count,
            messages.SUCCESS,
        )

    def mark_as_unread(self, request, queryset: QuerySet):
        bookmarks_count = queryset.count()
        queryset.update(unread=True)
        self.message_user(
            request,
            ngettext(
                "%d bookmark marked as unread.",
                "%d bookmarks marked as unread.",
                bookmarks_count,
            )
            % bookmarks_count,
            messages.SUCCESS,
        )


class AdminBookmarkAsset(admin.ModelAdmin):
    @admin.display(description="Display Name")
    def custom_display_name(self, obj):
        return str(obj)

    list_display = ("custom_display_name", "date_created", "status")
    search_fields = (
        "custom_display_name",
        "file",
    )
    list_filter = ("status",)


class AdminTag(admin.ModelAdmin):
    list_display = ("name", "bookmarks_count", "owner", "date_added")
    search_fields = ("name", "owner__username")
    list_filter = ("owner__username",)
    ordering = ("-date_added",)
    actions = ["delete_unused_tags"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(bookmarks_count=Count("bookmark"))
        return queryset

    def bookmarks_count(self, obj):
        return obj.bookmarks_count

    bookmarks_count.admin_order_field = "bookmarks_count"

    def delete_unused_tags(self, request, queryset: QuerySet):
        unused_tags = queryset.filter(bookmark__isnull=True)
        unused_tags_count = unused_tags.count()
        for tag in unused_tags:
            tag.delete()

        if unused_tags_count > 0:
            self.message_user(
                request,
                ngettext(
                    "%d unused tag was successfully deleted.",
                    "%d unused tags were successfully deleted.",
                    unused_tags_count,
                )
                % unused_tags_count,
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                gettext(
                    "There were no unused tags in the selection",
                ),
                messages.SUCCESS,
            )


class AdminUserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"
    readonly_fields = ("search_preferences",)


class AdminCustomUser(UserAdmin):
    inlines = (AdminUserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(AdminCustomUser, self).get_inline_instances(request, obj)


class AdminToast(admin.ModelAdmin):
    list_display = ("key", "message", "owner", "acknowledged")
    search_fields = ("key", "message")
    list_filter = ("owner__username",)


class AdminFeedToken(admin.ModelAdmin):
    list_display = ("key", "user")
    search_fields = ["key"]
    list_filter = ("user__username",)


linkding_admin_site = LinkdingAdminSite()
linkding_admin_site.register(Bookmark, AdminBookmark)
linkding_admin_site.register(BookmarkAsset, AdminBookmarkAsset)
linkding_admin_site.register(Tag, AdminTag)
linkding_admin_site.register(User, AdminCustomUser)
linkding_admin_site.register(TokenProxy, TokenAdmin)
linkding_admin_site.register(Toast, AdminToast)
linkding_admin_site.register(FeedToken, AdminFeedToken)
