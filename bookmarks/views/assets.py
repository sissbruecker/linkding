import gzip
import os

from django.conf import settings
from django.http import (
    Http404,
    HttpResponse,
)
from django.shortcuts import render

from bookmarks.views import access


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
    asset = access.asset_read(request, asset_id)
    content = _get_asset_content(asset)

    response = HttpResponse(content, content_type=asset.content_type)
    response["Content-Disposition"] = f'inline; filename="{asset.download_name}"'
    if asset.content_type and asset.content_type.startswith("video/"):
        response["Content-Security-Policy"] = "default-src 'none'; media-src 'self';"
    elif asset.content_type == "application/pdf":
        response["Content-Security-Policy"] = "default-src 'none'; object-src 'self';"
    else:
        response["Content-Security-Policy"] = "sandbox allow-scripts"
    return response


def read(request, asset_id: int):
    asset = access.asset_read(request, asset_id)
    content = _get_asset_content(asset)
    content = content.decode("utf-8")

    return render(
        request,
        "bookmarks/read.html",
        {
            "content": content,
        },
    )
