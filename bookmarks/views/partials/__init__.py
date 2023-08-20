from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from bookmarks.views.partials import contexts


@login_required
def bookmark_list(request):
    bookmark_list_context = contexts.ActiveBookmarkListContext(request)

    return render(request, 'bookmarks/bookmark_list.html', {
        'bookmark_list': bookmark_list_context
    })


@login_required
def tag_cloud(request):
    tag_cloud_context = contexts.ActiveTagCloudContext(request)

    return render(request, 'bookmarks/tag_cloud.html', {
        'tag_cloud': tag_cloud_context
    })