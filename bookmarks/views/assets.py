from django.http import Http404
from django.shortcuts import render

from bookmarks.services import assets
from bookmarks.views import access


def view(request, asset_id: int):
    asset = access.asset_read(request, asset_id)
    try:
        response = assets.stream_asset_file(asset)
    except FileNotFoundError:
        raise Http404("Asset file does not exist") from None

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
    try:
        with assets.open_asset_file(asset) as file:
            content = file.read().decode("utf-8")
    except FileNotFoundError:
        raise Http404("Asset file does not exist") from None

    response = render(
        request,
        "bookmarks/read.html",
        {
            "content": content,
        },
    )
    response["Content-Security-Policy"] = "sandbox allow-scripts"
    return response
