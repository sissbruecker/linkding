from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from bookmarks.models import Bookmark
from bookmarks.views.partials import contexts


@login_required
def active_bookmark_list(request):
    bookmark_list_context = contexts.ActiveBookmarkListContext(request)

    return render(
        request,
        "bookmarks/bookmark_list.html",
        {"bookmark_list": bookmark_list_context},
    )


@login_required
def active_tag_cloud(request):
    tag_cloud_context = contexts.ActiveTagCloudContext(request)

    return render(request, "bookmarks/tag_cloud.html", {"tag_cloud": tag_cloud_context})


@login_required
def archived_bookmark_list(request):
    bookmark_list_context = contexts.ArchivedBookmarkListContext(request)

    return render(
        request,
        "bookmarks/bookmark_list.html",
        {"bookmark_list": bookmark_list_context},
    )


@login_required
def archived_tag_cloud(request):
    tag_cloud_context = contexts.ArchivedTagCloudContext(request)

    return render(request, "bookmarks/tag_cloud.html", {"tag_cloud": tag_cloud_context})


@login_required
def shared_bookmark_list(request):
    bookmark_list_context = contexts.SharedBookmarkListContext(request)

    return render(
        request,
        "bookmarks/bookmark_list.html",
        {"bookmark_list": bookmark_list_context},
    )


@login_required
def shared_tag_cloud(request):
    tag_cloud_context = contexts.SharedTagCloudContext(request)

    return render(request, "bookmarks/tag_cloud.html", {"tag_cloud": tag_cloud_context})


@login_required
def details_form(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")

    details_context = contexts.BookmarkDetailsContext(request, bookmark)

    return render(request, "bookmarks/details/form.html", {"details": details_context})
