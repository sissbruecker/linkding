from django.http import Http404

from bookmarks.models import Bookmark, BookmarkAsset, BookmarkBundle, Toast
from bookmarks.type_defs import HttpRequest


def bookmark_read(request: HttpRequest, bookmark_id: int | str):
    try:
        bookmark = Bookmark.objects.get(pk=int(bookmark_id))
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
    if request.method == "POST" and not is_owner:
        raise Http404("Bookmark does not exist")

    return bookmark


def bookmark_write(request: HttpRequest, bookmark_id: int | str):
    try:
        return Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404("Bookmark does not exist")


def bundle_read(request: HttpRequest, bundle_id: int | str):
    return bundle_write(request, bundle_id)


def bundle_write(request: HttpRequest, bundle_id: int | str):
    try:
        return BookmarkBundle.objects.get(pk=bundle_id, owner=request.user)
    except (BookmarkBundle.DoesNotExist, ValueError):
        raise Http404("Bundle does not exist")


def asset_read(request: HttpRequest, asset_id: int | str):
    try:
        asset = BookmarkAsset.objects.get(pk=asset_id)
    except BookmarkAsset.DoesNotExist:
        raise Http404("Asset does not exist")

    bookmark_read(request, asset.bookmark_id)
    return asset


def asset_write(request: HttpRequest, asset_id: int | str):
    try:
        return BookmarkAsset.objects.get(pk=asset_id, bookmark__owner=request.user)
    except BookmarkAsset.DoesNotExist:
        raise Http404("Asset does not exist")


def toast_write(request: HttpRequest, toast_id: int | str):
    try:
        return Toast.objects.get(pk=toast_id, owner=request.user)
    except Toast.DoesNotExist:
        raise Http404("Toast does not exist")
