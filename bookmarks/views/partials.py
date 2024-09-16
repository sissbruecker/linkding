from bookmarks.views import contexts, turbo


def render_bookmark_update(request, bookmark_list, tag_cloud, details):
    return turbo.stream(
        request,
        "bookmarks/updates/bookmark_view_stream.html",
        {
            "bookmark_list": bookmark_list,
            "tag_cloud": tag_cloud,
            "details": details,
        },
    )


def active_bookmark_update(request):
    bookmark_list = contexts.ActiveBookmarkListContext(request)
    tag_cloud = contexts.ActiveTagCloudContext(request)
    details = contexts.get_details_context(
        request, contexts.ActiveBookmarkDetailsContext
    )
    return render_bookmark_update(request, bookmark_list, tag_cloud, details)


def archived_bookmark_update(request):
    bookmark_list = contexts.ArchivedBookmarkListContext(request)
    tag_cloud = contexts.ArchivedTagCloudContext(request)
    details = contexts.get_details_context(
        request, contexts.ArchivedBookmarkDetailsContext
    )
    return render_bookmark_update(request, bookmark_list, tag_cloud, details)


def shared_bookmark_update(request):
    bookmark_list = contexts.SharedBookmarkListContext(request)
    tag_cloud = contexts.SharedTagCloudContext(request)
    details = contexts.get_details_context(
        request, contexts.SharedBookmarkDetailsContext
    )
    return render_bookmark_update(request, bookmark_list, tag_cloud, details)
