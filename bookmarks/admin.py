import os

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, QuerySet
from django.shortcuts import render
from django.urls import path
from django.utils.translation import gettext, ngettext
from huey.contrib.djhuey import HUEY as huey

from bookmarks.models import (
    ApiToken,
    Bookmark,
    BookmarkAsset,
    BookmarkBundle,
    FeedToken,
    Tag,
    Toast,
    UserProfile,
)
from bookmarks.services import tags as tag_service
from bookmarks.services import tasks
from bookmarks.services.bookmarks import (
    archive_bookmark,
    delete_bookmark,
    unarchive_bookmark,
)


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
        def to_bytes(b):
            return bytes(b) if not isinstance(b, bytes) else b

        sql = "select data from task where queue=? order by priority desc, id limit ? offset ?"
        params = (huey.storage.name, limit, offset)

        serialized_tasks = [
            to_bytes(i) for (i,) in huey.storage.sql(sql, params, results=True)
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
            path(
                "tasks/",
                self.admin_view(background_task_view),
                name="background_tasks",
            ),
        ]
        return custom_urls + urls

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        context_path = os.getenv("LD_CONTEXT_PATH", "")
        app_list += [
            {
                "name": "Huey",
                "app_label": "huey_app",
                "models": [
                    {
                        "name": "Queued tasks",
                        "object_name": "background_tasks",
                        "admin_url": f"/{context_path}admin/tasks/",
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

    def save_model(self, request, obj, form, change):
        # Track changes for the previous and the new owner, as moving a bookmark
        # to another user is reported as a deletion and a creation. Changes are
        # completed in save_related, after saving tags.
        owners = [obj.owner]
        if change:
            previous_owner = Bookmark.objects.get(pk=obj.pk).owner
            if previous_owner != obj.owner:
                owners.append(previous_owner)
        bookmark_changes = [tasks.BookmarkChanges(owner) for owner in owners]
        # Tags must be locked before the bookmark, see lock_tags
        bookmark_changes[0].lock_tags(form.cleaned_data.get("tags", []))
        if change:
            for changes in bookmark_changes:
                changes.track([obj.pk])

        super().save_model(request, obj, form, change)

        # Does nothing if the bookmark was already tracked for the owner
        bookmark_changes[0].track_created(obj)
        request._bookmark_changes = bookmark_changes

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # The admin saves the form in a transaction, so events are only sent
        # once it commits
        for changes in getattr(request, "_bookmark_changes", []):
            changes.send_events()

    def delete_model(self, request, obj):
        delete_bookmark(obj)

    def delete_selected_bookmarks(self, request, queryset: QuerySet):
        bookmarks_count = queryset.count()
        for bookmark in queryset:
            delete_bookmark(bookmark)
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
        self._update_bookmarks(queryset, unread=False)
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
        self._update_bookmarks(queryset, unread=True)
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

    def _update_bookmarks(self, queryset: QuerySet, **fields):
        # Resolve IDs first, as the queryset may be filtered by the fields that
        # are updated
        bookmark_ids = list(queryset.values_list("id", flat=True))
        with tasks.track_bookmark_changes_of_all_owners(bookmark_ids):
            Bookmark.objects.filter(id__in=bookmark_ids).update(**fields)


class AdminBookmarkAsset(admin.ModelAdmin):
    @admin.display(description="Display Name")
    def custom_display_name(self, obj):
        return str(obj)

    list_display = ("custom_display_name", "date_created", "status")
    search_fields = (
        "display_name",
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

    def save_model(self, request, obj, form, change):
        if not change:
            return super().save_model(request, obj, form, change)
        # Renaming a tag changes the tags of all of its bookmarks
        with tag_service.track_tag_changes([obj]):
            super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        tag_service.delete_tag(obj)

    def delete_queryset(self, request, queryset):
        with tag_service.track_tag_changes(queryset):
            super().delete_queryset(request, queryset)

    def delete_unused_tags(self, request, queryset: QuerySet):
        unused_tags = queryset.filter(bookmark__isnull=True)
        unused_tags_count = unused_tags.count()
        for tag in unused_tags:
            # The tag may have been added to a bookmark in the meantime
            tag_service.delete_tag(tag)

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


class AdminBookmarkBundle(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "order",
        "search",
        "any_tags",
        "all_tags",
        "excluded_tags",
        "filter_shared",
        "filter_unread",
        "date_created",
    )
    search_fields = ["name", "search", "any_tags", "all_tags", "excluded_tags"]
    list_filter = ("owner__username",)


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
        return super().get_inline_instances(request, obj)


class AdminToast(admin.ModelAdmin):
    list_display = ("key", "message", "owner", "acknowledged")
    search_fields = ("key", "message")
    list_filter = ("owner__username",)


class AdminFeedToken(admin.ModelAdmin):
    list_display = ("key", "user")
    search_fields = ["key"]
    list_filter = ("user__username",)


class ApiTokenAdminForm(forms.ModelForm):
    class Meta:
        model = ApiToken
        fields = ("name", "user")


class AdminApiToken(admin.ModelAdmin):
    form = ApiTokenAdminForm
    list_display = ("name", "user", "created")
    search_fields = ["name", "user__username"]
    list_filter = ("user__username",)
    ordering = ("-created",)


linkding_admin_site = LinkdingAdminSite()
linkding_admin_site.register(Bookmark, AdminBookmark)
linkding_admin_site.register(BookmarkAsset, AdminBookmarkAsset)
linkding_admin_site.register(Tag, AdminTag)
linkding_admin_site.register(BookmarkBundle, AdminBookmarkBundle)
linkding_admin_site.register(User, AdminCustomUser)
linkding_admin_site.register(ApiToken, AdminApiToken)
linkding_admin_site.register(Toast, AdminToast)
linkding_admin_site.register(FeedToken, AdminFeedToken)
