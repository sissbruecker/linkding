import urllib.parse
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet, F
from django.http import (
    HttpResponseRedirect,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from bookmarks import queries, utils
from bookmarks.forms import BookmarkForm
from bookmarks.models import (
    Bookmark,
    BookmarkSearch,
)
from bookmarks.services import assets as asset_actions, tasks
from bookmarks.services.bookmarks import (
    archive_bookmark,
    archive_bookmarks,
    unarchive_bookmark,
    unarchive_bookmarks,
    delete_bookmarks,
    tag_bookmarks,
    untag_bookmarks,
    mark_bookmarks_as_read,
    mark_bookmarks_as_unread,
    share_bookmarks,
    unshare_bookmarks,
    refresh_bookmarks_metadata,
    create_html_snapshots,
)
from bookmarks.type_defs import HttpRequest
from bookmarks.utils import get_safe_return_url
from bookmarks.views import access, contexts, partials, turbo


@login_required
def index(request: HttpRequest):
    if request.method == "POST":
        return search_action(request)

    search = BookmarkSearch.from_request(
        request, request.GET, request.user_profile.search_preferences
    )
    bookmark_list = contexts.ActiveBookmarkListContext(request, search)
    bundles = contexts.BundlesContext(request)
    tag_cloud = contexts.ActiveTagCloudContext(request, search)
    bookmark_details = contexts.get_details_context(
        request, contexts.ActiveBookmarkDetailsContext
    )

    return render_bookmarks_view(
        request,
        "bookmarks/index.html",
        {
            "page_title": "Bookmarks - Linkding",
            "bookmark_list": bookmark_list,
            "bundles": bundles,
            "tag_cloud": tag_cloud,
            "details": bookmark_details,
        },
    )


@login_required
def archived(request: HttpRequest):
    if request.method == "POST":
        return search_action(request)

    search = BookmarkSearch.from_request(
        request, request.GET, request.user_profile.search_preferences
    )
    bookmark_list = contexts.ArchivedBookmarkListContext(request, search)
    bundles = contexts.BundlesContext(request)
    tag_cloud = contexts.ArchivedTagCloudContext(request, search)
    bookmark_details = contexts.get_details_context(
        request, contexts.ArchivedBookmarkDetailsContext
    )

    return render_bookmarks_view(
        request,
        "bookmarks/archive.html",
        {
            "page_title": "Archived bookmarks - Linkding",
            "bookmark_list": bookmark_list,
            "bundles": bundles,
            "tag_cloud": tag_cloud,
            "details": bookmark_details,
        },
    )


def shared(request: HttpRequest):
    if request.method == "POST":
        return search_action(request)

    search = BookmarkSearch.from_request(
        request, request.GET, request.user_profile.search_preferences
    )
    bookmark_list = contexts.SharedBookmarkListContext(request, search)
    tag_cloud = contexts.SharedTagCloudContext(request, search)
    bookmark_details = contexts.get_details_context(
        request, contexts.SharedBookmarkDetailsContext
    )
    public_only = not request.user.is_authenticated
    users = queries.query_shared_bookmark_users(
        request.user_profile, bookmark_list.search, public_only
    )
    return render_bookmarks_view(
        request,
        "bookmarks/shared.html",
        {
            "page_title": "Shared bookmarks - Linkding",
            "bookmark_list": bookmark_list,
            "tag_cloud": tag_cloud,
            "details": bookmark_details,
            "users": users,
            "rss_feed_url": reverse("linkding:feeds.public_shared"),
        },
    )


def render_bookmarks_view(request: HttpRequest, template_name, context):
    if context["details"]:
        context["page_title"] = "Bookmark details - Linkding"

    if turbo.is_frame(request, "details-modal"):
        return render(
            request,
            "bookmarks/updates/details-modal-frame.html",
            context,
        )

    return render(
        request,
        template_name,
        context,
    )


def search_action(request: HttpRequest):
    if "save" in request.POST:
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        search = BookmarkSearch.from_request(request, request.POST)
        request.user_profile.search_preferences = search.preferences_dict
        request.user_profile.save()

    # redirect to base url including new query params
    search = BookmarkSearch.from_request(
        request, request.POST, request.user_profile.search_preferences
    )
    base_url = request.path
    query_params = search.query_params
    query_string = urllib.parse.urlencode(query_params)
    url = base_url if not query_string else base_url + "?" + query_string
    return HttpResponseRedirect(url)


def convert_tag_string(tag_string: str):
    # Tag strings coming from inputs are space-separated, however services.bookmarks functions expect comma-separated
    # strings
    return tag_string.replace(" ", ",")


@login_required
def new(request: HttpRequest):
    form = BookmarkForm(request)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            if form.is_auto_close:
                return HttpResponseRedirect(reverse("linkding:bookmarks.close"))
            else:
                return HttpResponseRedirect(reverse("linkding:bookmarks.index"))

    status = 422 if request.method == "POST" and not form.is_valid() else 200
    context = {"form": form, "return_url": reverse("linkding:bookmarks.index")}

    return render(request, "bookmarks/new.html", context, status=status)


@login_required
def edit(request: HttpRequest, bookmark_id: int):
    bookmark = access.bookmark_write(request, bookmark_id)
    form = BookmarkForm(request, instance=bookmark)
    return_url = get_safe_return_url(
        request.GET.get("return_url"), reverse("linkding:bookmarks.index")
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(return_url)

    status = 422 if request.method == "POST" and not form.is_valid() else 200
    context = {"form": form, "bookmark_id": bookmark_id, "return_url": return_url}

    return render(request, "bookmarks/edit.html", context, status=status)


def remove(request: HttpRequest, bookmark_id: int | str):
    bookmark = access.bookmark_write(request, bookmark_id)
    bookmark.delete()


def archive(request: HttpRequest, bookmark_id: int | str):
    bookmark = access.bookmark_write(request, bookmark_id)
    archive_bookmark(bookmark)


def unarchive(request: HttpRequest, bookmark_id: int | str):
    bookmark = access.bookmark_write(request, bookmark_id)
    unarchive_bookmark(bookmark)


def unshare(request: HttpRequest, bookmark_id: int | str):
    bookmark = access.bookmark_write(request, bookmark_id)
    bookmark.shared = False
    bookmark.save()


def mark_as_read(request: HttpRequest, bookmark_id: int | str):
    bookmark = access.bookmark_write(request, bookmark_id)
    bookmark.unread = False
    bookmark.save()


def create_html_snapshot(request: HttpRequest, bookmark_id: int | str):
    bookmark = access.bookmark_write(request, bookmark_id)
    tasks.create_html_snapshot(bookmark)


def upload_asset(request: HttpRequest, bookmark_id: int | str):
    if settings.LD_DISABLE_ASSET_UPLOAD:
        return HttpResponseForbidden("Asset upload is disabled")

    bookmark = access.bookmark_write(request, bookmark_id)
    file = request.FILES.get("upload_asset_file")
    if not file:
        return HttpResponseBadRequest("No file provided")

    asset_actions.upload_asset(bookmark, file)


def remove_asset(request: HttpRequest, asset_id: int | str):
    asset = access.asset_write(request, asset_id)
    asset_actions.remove_asset(asset)


def update_state(request: HttpRequest, bookmark_id: int | str):
    bookmark = access.bookmark_write(request, bookmark_id)
    bookmark.is_archived = request.POST.get("is_archived") == "on"
    bookmark.unread = request.POST.get("unread") == "on"
    bookmark.shared = request.POST.get("shared") == "on"
    bookmark.save()


@login_required
def index_action(request: HttpRequest):
    search = BookmarkSearch.from_request(
        request, request.GET, request.user_profile.search_preferences
    )
    query = queries.query_bookmarks(request.user, request.user_profile, search)

    response = handle_action(request, query)
    if response:
        return response

    if turbo.accept(request):
        return partials.active_bookmark_update(request)

    return utils.redirect_with_query(request, reverse("linkding:bookmarks.index"))


@login_required
def archived_action(request: HttpRequest):
    search = BookmarkSearch.from_request(
        request, request.GET, request.user_profile.search_preferences
    )
    query = queries.query_archived_bookmarks(request.user, request.user_profile, search)

    response = handle_action(request, query)
    if response:
        return response

    if turbo.accept(request):
        return partials.archived_bookmark_update(request)

    return utils.redirect_with_query(request, reverse("linkding:bookmarks.archived"))


@login_required
def shared_action(request: HttpRequest):
    if "bulk_execute" in request.POST:
        return HttpResponseBadRequest("View does not support bulk actions")

    response = handle_action(request)
    if response:
        return response

    if turbo.accept(request):
        return partials.shared_bookmark_update(request)

    return utils.redirect_with_query(request, reverse("linkding:bookmarks.shared"))


def handle_action(request: HttpRequest, query: QuerySet[Bookmark] = None):
    # Single bookmark actions
    if "archive" in request.POST:
        return archive(request, request.POST["archive"])
    if "unarchive" in request.POST:
        return unarchive(request, request.POST["unarchive"])
    if "remove" in request.POST:
        return remove(request, request.POST["remove"])
    if "mark_as_read" in request.POST:
        return mark_as_read(request, request.POST["mark_as_read"])
    if "unshare" in request.POST:
        return unshare(request, request.POST["unshare"])
    if "create_html_snapshot" in request.POST:
        return create_html_snapshot(request, request.POST["create_html_snapshot"])
    if "upload_asset" in request.POST:
        return upload_asset(request, request.POST["upload_asset"])
    if "remove_asset" in request.POST:
        return remove_asset(request, request.POST["remove_asset"])

    # State updates
    if "update_state" in request.POST:
        return update_state(request, request.POST["update_state"])

    # Bulk actions
    if "bulk_execute" in request.POST:
        if query is None:
            raise ValueError("Query must be provided for bulk actions")

        bulk_action = request.POST["bulk_action"]

        # Determine set of bookmarks
        if request.POST.get("bulk_select_across") == "on":
            # Query full list of bookmarks across all pages
            bookmark_ids = query.only("id").values_list("id", flat=True)
        else:
            # Use only selected bookmarks
            bookmark_ids = request.POST.getlist("bookmark_id")

        if "bulk_archive" == bulk_action:
            return archive_bookmarks(bookmark_ids, request.user)
        if "bulk_unarchive" == bulk_action:
            return unarchive_bookmarks(bookmark_ids, request.user)
        if "bulk_delete" == bulk_action:
            return delete_bookmarks(bookmark_ids, request.user)
        if "bulk_tag" == bulk_action:
            tag_string = convert_tag_string(request.POST["bulk_tag_string"])
            return tag_bookmarks(bookmark_ids, tag_string, request.user)
        if "bulk_untag" == bulk_action:
            tag_string = convert_tag_string(request.POST["bulk_tag_string"])
            return untag_bookmarks(bookmark_ids, tag_string, request.user)
        if "bulk_read" == bulk_action:
            return mark_bookmarks_as_read(bookmark_ids, request.user)
        if "bulk_unread" == bulk_action:
            return mark_bookmarks_as_unread(bookmark_ids, request.user)
        if "bulk_share" == bulk_action:
            return share_bookmarks(bookmark_ids, request.user)
        if "bulk_unshare" == bulk_action:
            return unshare_bookmarks(bookmark_ids, request.user)
        if "bulk_refresh" == bulk_action:
            return refresh_bookmarks_metadata(bookmark_ids, request.user)
        if "bulk_snapshot" == bulk_action:
            return create_html_snapshots(bookmark_ids, request.user)


@login_required
def visit(request: HttpRequest, bookmark_id: int):
    bookmark = get_object_or_404(Bookmark, id=bookmark_id, owner=request.user)
    
    # Increment access count and update last accessed time
    Bookmark.objects.filter(id=bookmark_id).update(
        access_count=F('access_count') + 1,
        date_accessed=timezone.now()
    )
    
    return HttpResponseRedirect(bookmark.url)


@login_required
def close(request: HttpRequest):
    return render(request, "bookmarks/close.html")
