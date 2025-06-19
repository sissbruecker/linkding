from bookmarks.models import BookmarkSearch
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
    search = BookmarkSearch.from_request(
        request, request.GET, request.user_profile.search_preferences
    )
    bookmark_list = contexts.ActiveBookmarkListContext(request, search)
    tag_cloud = contexts.ActiveTagCloudContext(request, search)
    details = contexts.get_details_context(
        request, contexts.ActiveBookmarkDetailsContext
    )
    return render_bookmark_update(request, bookmark_list, tag_cloud, details)


def archived_bookmark_update(request):
    search = BookmarkSearch.from_request(
        request, request.GET, request.user_profile.search_preferences
    )
    bookmark_list = contexts.ArchivedBookmarkListContext(request, search)
    tag_cloud = contexts.ArchivedTagCloudContext(request, search)
    details = contexts.get_details_context(
        request, contexts.ArchivedBookmarkDetailsContext
    )
    return render_bookmark_update(request, bookmark_list, tag_cloud, details)


def shared_bookmark_update(request):
    search = BookmarkSearch.from_request(
        request, request.GET, request.user_profile.search_preferences
    )
    bookmark_list = contexts.SharedBookmarkListContext(request, search)
    tag_cloud = contexts.SharedTagCloudContext(request, search)
    details = contexts.get_details_context(
        request, contexts.SharedBookmarkDetailsContext
    )
    return render_bookmark_update(request, bookmark_list, tag_cloud, details)
