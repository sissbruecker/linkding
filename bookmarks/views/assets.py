import gzip
import os

from django.conf import settings
from django.http import (
    HttpResponse,
    Http404,
)
from django.shortcuts import render

from bookmarks.models import BookmarkAsset


def _access_asset(request, asset_id: int):
    try:
        asset = BookmarkAsset.objects.get(pk=asset_id)
    except BookmarkAsset.DoesNotExist:
        raise Http404("Asset does not exist")

    bookmark = asset.bookmark
    is_owner = bookmark.owner == request.user
    is_shared = (
        request.user.is_authenticated
        and bookmark.shared
        and bookmark.owner.profile.enable_sharing
    )
    is_public_shared = bookmark.shared and bookmark.owner.profile.enable_public_sharing

    if not is_owner and not is_shared and not is_public_shared:
        raise Http404("Bookmark does not exist")

    return asset


def _get_asset_content(asset):
    filepath = os.path.join(settings.LD_ASSET_FOLDER, asset.file)

    if not os.path.exists(filepath):
        raise Http404("Asset file does not exist")

    if asset.gzip:
        with gzip.open(filepath, "rb") as f:
            content = f.read()
    else:
        with open(filepath, "rb") as f:
            content = f.read()

    return content


def view(request, asset_id: int):
    asset = _access_asset(request, asset_id)
    content = _get_asset_content(asset)

    return HttpResponse(content, content_type=asset.content_type)


def read(request, asset_id: int):
    asset = _access_asset(request, asset_id)
    content = _get_asset_content(asset)
    content = content.decode("utf-8")

    return render(
        request,
        "bookmarks/read.html",
        {
            "content": content,
        },
    )
