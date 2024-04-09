from django.contrib.auth.decorators import login_required
from django.shortcuts import render

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
def active_tag_modal(request):
    tag_cloud_context = contexts.ActiveTagCloudContext(request)

    return render(request, "bookmarks/tag_modal.html", {"tag_cloud": tag_cloud_context})


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
def archived_tag_modal(request):
    tag_cloud_context = contexts.ArchivedTagCloudContext(request)

    return render(request, "bookmarks/tag_modal.html", {"tag_cloud": tag_cloud_context})


def shared_bookmark_list(request):
    bookmark_list_context = contexts.SharedBookmarkListContext(request)

    return render(
        request,
        "bookmarks/bookmark_list.html",
        {"bookmark_list": bookmark_list_context},
    )


def shared_tag_cloud(request):
    tag_cloud_context = contexts.SharedTagCloudContext(request)

    return render(request, "bookmarks/tag_cloud.html", {"tag_cloud": tag_cloud_context})


def shared_tag_modal(request):
    tag_cloud_context = contexts.SharedTagCloudContext(request)

    return render(request, "bookmarks/tag_modal.html", {"tag_cloud": tag_cloud_context})
