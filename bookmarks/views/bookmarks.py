import urllib.parse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import (
    HttpResponseRedirect,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import render
from django.urls import reverse

from bookmarks import queries, utils
from bookmarks.models import (
    Bookmark,
    BookmarkForm,
    BookmarkSearch,
    build_tag_string,
)
from bookmarks.services import assets as asset_actions, tasks
from bookmarks.services.bookmarks import (
    create_bookmark,
    update_bookmark,
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
)
from bookmarks.type_defs import HttpRequest
from bookmarks.utils import get_safe_return_url
from bookmarks.views import access, contexts, partials, turbo


@login_required
def index(request: HttpRequest):
    if request.method == "POST":
        return search_action(request)

    bookmark_list = contexts.ActiveBookmarkListContext(request)
    tag_cloud = contexts.ActiveTagCloudContext(request)
    bookmark_details = contexts.get_details_context(
        request, contexts.ActiveBookmarkDetailsContext
    )

    return render_bookmarks_view(
        request,
        "bookmarks/index.html",
        {
            "bookmark_list": bookmark_list,
            "tag_cloud": tag_cloud,
            "details": bookmark_details,
        },
    )


@login_required
def archived(request: HttpRequest):
    if request.method == "POST":
        return search_action(request)

    bookmark_list = contexts.ArchivedBookmarkListContext(request)
    tag_cloud = contexts.ArchivedTagCloudContext(request)
    bookmark_details = contexts.get_details_context(
        request, contexts.ArchivedBookmarkDetailsContext
    )

    return render_bookmarks_view(
        request,
        "bookmarks/archive.html",
        {
            "bookmark_list": bookmark_list,
            "tag_cloud": tag_cloud,
            "details": bookmark_details,
        },
    )


def shared(request: HttpRequest):
    if request.method == "POST":
        return search_action(request)

    bookmark_list = contexts.SharedBookmarkListContext(request)
    tag_cloud = contexts.SharedTagCloudContext(request)
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
            "bookmark_list": bookmark_list,
            "tag_cloud": tag_cloud,
            "details": bookmark_details,
            "users": users,
            "rss_feed_url": reverse("linkding:feeds.public_shared"),
        },
    )


def render_bookmarks_view(request: HttpRequest, template_name, context):
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
        search = BookmarkSearch.from_request(request.POST)
        request.user_profile.search_preferences = search.preferences_dict
        request.user_profile.save()

    # redirect to base url including new query params
    search = BookmarkSearch.from_request(
        request.POST, request.user_profile.search_preferences
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
    initial_auto_close = True if "auto_close" in request.GET else None

    if request.method == "POST":
        form = BookmarkForm(request.POST)
        auto_close = form.data["auto_close"]
        if form.is_valid():
            current_user = request.user
            tag_string = convert_tag_string(form.data["tag_string"])
            create_bookmark(form.save(commit=False), tag_string, current_user)
            if auto_close:
                return HttpResponseRedirect(reverse("linkding:bookmarks.close"))
            else:
                return HttpResponseRedirect(reverse("linkding:bookmarks.index"))
    else:
        form = BookmarkForm(
            initial={
                "url": request.GET.get("url"),
                "title": request.GET.get("title"),
                "description": request.GET.get("description"),
                "notes": request.GET.get("notes"),
                "auto_close": initial_auto_close,
                "unread": request.user_profile.default_mark_unread,
            }
        )

    status = 422 if request.method == "POST" and not form.is_valid() else 200
    context = {
        "form": form,
        "auto_close": initial_auto_close,
        "return_url": reverse("linkding:bookmarks.index"),
    }

    return render(request, "bookmarks/new.html", context, status=status)


@login_required
def edit(request: HttpRequest, bookmark_id: int):
    bookmark = access.bookmark_write(request, bookmark_id)
    return_url = get_safe_return_url(
        request.GET.get("return_url"), reverse("linkding:bookmarks.index")
    )

    if request.method == "POST":
        form = BookmarkForm(request.POST, instance=bookmark)
        if form.is_valid():
            tag_string = convert_tag_string(form.data["tag_string"])
            update_bookmark(form.save(commit=False), tag_string, request.user)
            return HttpResponseRedirect(return_url)
    else:
        form = BookmarkForm(instance=bookmark)

    form.fields["tag_string"].initial = build_tag_string(bookmark.tag_names, " ")

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
    asset.delete()


def update_state(request: HttpRequest, bookmark_id: int | str):
    bookmark = access.bookmark_write(request, bookmark_id)
    bookmark.is_archived = request.POST.get("is_archived") == "on"
    bookmark.unread = request.POST.get("unread") == "on"
    bookmark.shared = request.POST.get("shared") == "on"
    bookmark.save()


@login_required
def index_action(request: HttpRequest):
    search = BookmarkSearch.from_request(request.GET)
    query = queries.query_bookmarks(request.user, request.user_profile, search)

    response = handle_action(request, query)
    if response:
        return response

    if turbo.accept(request):
        return partials.active_bookmark_update(request)

    return utils.redirect_with_query(request, reverse("linkding:bookmarks.index"))


@login_required
def archived_action(request: HttpRequest):
    search = BookmarkSearch.from_request(request.GET)
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


@login_required
def close(request: HttpRequest):
    return render(request, "bookmarks/close.html")
