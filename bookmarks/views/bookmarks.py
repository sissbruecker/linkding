import urllib.parse

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import (
    HttpResponseRedirect,
    Http404,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import render
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import (
    Bookmark,
    BookmarkAsset,
    BookmarkForm,
    BookmarkSearch,
    build_tag_string,
)
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
from bookmarks.services import tasks
from bookmarks.utils import get_safe_return_url
from bookmarks.views.partials import contexts

_default_page_size = 30


@login_required
def index(request):
    if request.method == "POST":
        return search_action(request)

    bookmark_list = contexts.ActiveBookmarkListContext(request)
    tag_cloud = contexts.ActiveTagCloudContext(request)
    return render(
        request,
        "bookmarks/index.html",
        {
            "bookmark_list": bookmark_list,
            "tag_cloud": tag_cloud,
        },
    )


@login_required
def archived(request):
    if request.method == "POST":
        return search_action(request)

    bookmark_list = contexts.ArchivedBookmarkListContext(request)
    tag_cloud = contexts.ArchivedTagCloudContext(request)
    return render(
        request,
        "bookmarks/archive.html",
        {
            "bookmark_list": bookmark_list,
            "tag_cloud": tag_cloud,
        },
    )


def shared(request):
    if request.method == "POST":
        return search_action(request)

    bookmark_list = contexts.SharedBookmarkListContext(request)
    tag_cloud = contexts.SharedTagCloudContext(request)
    public_only = not request.user.is_authenticated
    users = queries.query_shared_bookmark_users(
        request.user_profile, bookmark_list.search, public_only
    )
    return render(
        request,
        "bookmarks/shared.html",
        {"bookmark_list": bookmark_list, "tag_cloud": tag_cloud, "users": users},
    )


def search_action(request):
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


def _details(request, bookmark_id: int, template: str):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")

    is_owner = bookmark.owner == request.user
    is_shared = (
        request.user.is_authenticated
        and bookmark.shared
        and bookmark.owner.profile.enable_sharing
    )
    is_public_shared = bookmark.shared and bookmark.owner.profile.enable_public_sharing
    if not is_owner and not is_shared and not is_public_shared:
        raise Http404("Bookmark does not exist")

    if request.method == "POST":
        if not is_owner:
            raise Http404("Bookmark does not exist")

        return_url = get_safe_return_url(
            request.GET.get("return_url"),
            reverse("bookmarks:details", args=[bookmark.id]),
        )

        if "remove_asset" in request.POST:
            asset_id = request.POST["remove_asset"]
            try:
                asset = bookmark.bookmarkasset_set.get(pk=asset_id)
            except BookmarkAsset.DoesNotExist:
                raise Http404("Asset does not exist")
            asset.delete()
        if "create_snapshot" in request.POST:
            tasks.create_html_snapshot(bookmark)
        else:
            bookmark.is_archived = request.POST.get("is_archived") == "on"
            bookmark.unread = request.POST.get("unread") == "on"
            bookmark.shared = request.POST.get("shared") == "on"
            bookmark.save()

        return HttpResponseRedirect(return_url)

    details_context = contexts.BookmarkDetailsContext(request, bookmark)

    return render(
        request,
        template,
        {
            "details": details_context,
        },
    )


def details(request, bookmark_id: int):
    return _details(request, bookmark_id, "bookmarks/details.html")


def details_modal(request, bookmark_id: int):
    return _details(request, bookmark_id, "bookmarks/details_modal.html")


def details_assets(request, bookmark_id: int):
    return _details(request, bookmark_id, "bookmarks/details/assets.html")


def convert_tag_string(tag_string: str):
    # Tag strings coming from inputs are space-separated, however services.bookmarks functions expect comma-separated
    # strings
    return tag_string.replace(" ", ",")


@login_required
def new(request):
    initial_url = request.GET.get("url")
    initial_title = request.GET.get("title")
    initial_description = request.GET.get("description")
    initial_auto_close = "auto_close" in request.GET
    initial_mark_unread = request.user.profile.default_mark_unread

    if request.method == "POST":
        form = BookmarkForm(request.POST)
        auto_close = form.data["auto_close"]
        if form.is_valid():
            current_user = request.user
            tag_string = convert_tag_string(form.data["tag_string"])
            create_bookmark(form.save(commit=False), tag_string, current_user)
            if auto_close:
                return HttpResponseRedirect(reverse("bookmarks:close"))
            else:
                return HttpResponseRedirect(reverse("bookmarks:index"))
    else:
        form = BookmarkForm()
        if initial_url:
            form.initial["url"] = initial_url
        if initial_title:
            form.initial["title"] = initial_title
        if initial_description:
            form.initial["description"] = initial_description
        if initial_auto_close:
            form.initial["auto_close"] = "true"
        if initial_mark_unread:
            form.initial["unread"] = "true"

    context = {
        "form": form,
        "auto_close": initial_auto_close,
        "return_url": reverse("bookmarks:index"),
    }

    return render(request, "bookmarks/new.html", context)


@login_required
def edit(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")
    return_url = get_safe_return_url(
        request.GET.get("return_url"), reverse("bookmarks:index")
    )

    if request.method == "POST":
        form = BookmarkForm(request.POST, instance=bookmark)
        if form.is_valid():
            tag_string = convert_tag_string(form.data["tag_string"])
            update_bookmark(form.save(commit=False), tag_string, request.user)
            return HttpResponseRedirect(return_url)
    else:
        form = BookmarkForm(instance=bookmark)

    form.initial["tag_string"] = build_tag_string(bookmark.tag_names, " ")

    context = {"form": form, "bookmark_id": bookmark_id, "return_url": return_url}

    return render(request, "bookmarks/edit.html", context)


def remove(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")

    bookmark.delete()


def archive(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")

    archive_bookmark(bookmark)


def unarchive(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")

    unarchive_bookmark(bookmark)


def unshare(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")

    bookmark.shared = False
    bookmark.save()


def mark_as_read(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")

    bookmark.unread = False
    bookmark.save()


@login_required
def index_action(request):
    search = BookmarkSearch.from_request(request.GET)
    query = queries.query_bookmarks(request.user, request.user_profile, search)
    return action(request, query)


@login_required
def archived_action(request):
    search = BookmarkSearch.from_request(request.GET)
    query = queries.query_archived_bookmarks(request.user, request.user_profile, search)
    return action(request, query)


@login_required
def shared_action(request):
    return action(request)


def action(request, query: QuerySet[Bookmark] = None):
    # Single bookmark actions
    if "archive" in request.POST:
        archive(request, request.POST["archive"])
    if "unarchive" in request.POST:
        unarchive(request, request.POST["unarchive"])
    if "remove" in request.POST:
        remove(request, request.POST["remove"])
    if "mark_as_read" in request.POST:
        mark_as_read(request, request.POST["mark_as_read"])
    if "unshare" in request.POST:
        unshare(request, request.POST["unshare"])

    # Bulk actions
    if "bulk_execute" in request.POST:
        if query is None:
            return HttpResponseBadRequest("View does not support bulk actions")

        bulk_action = request.POST["bulk_action"]

        # Determine set of bookmarks
        if request.POST.get("bulk_select_across") == "on":
            # Query full list of bookmarks across all pages
            bookmark_ids = query.only("id").values_list("id", flat=True)
        else:
            # Use only selected bookmarks
            bookmark_ids = request.POST.getlist("bookmark_id")

        if "bulk_archive" == bulk_action:
            archive_bookmarks(bookmark_ids, request.user)
        if "bulk_unarchive" == bulk_action:
            unarchive_bookmarks(bookmark_ids, request.user)
        if "bulk_delete" == bulk_action:
            delete_bookmarks(bookmark_ids, request.user)
        if "bulk_tag" == bulk_action:
            tag_string = convert_tag_string(request.POST["bulk_tag_string"])
            tag_bookmarks(bookmark_ids, tag_string, request.user)
        if "bulk_untag" == bulk_action:
            tag_string = convert_tag_string(request.POST["bulk_tag_string"])
            untag_bookmarks(bookmark_ids, tag_string, request.user)
        if "bulk_read" == bulk_action:
            mark_bookmarks_as_read(bookmark_ids, request.user)
        if "bulk_unread" == bulk_action:
            mark_bookmarks_as_unread(bookmark_ids, request.user)
        if "bulk_share" == bulk_action:
            share_bookmarks(bookmark_ids, request.user)
        if "bulk_unshare" == bulk_action:
            unshare_bookmarks(bookmark_ids, request.user)

    return_url = get_safe_return_url(
        request.GET.get("return_url"), reverse("bookmarks:index")
    )
    return HttpResponseRedirect(return_url)


@login_required
def close(request):
    return render(request, "bookmarks/close.html")
