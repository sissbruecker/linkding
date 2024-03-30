import gzip
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse,
    Http404,
)

from bookmarks.models import BookmarkAsset


@login_required
def view(request, asset_id: int):
    try:
        asset = BookmarkAsset.objects.get(pk=asset_id, bookmark__owner=request.user)
    except BookmarkAsset.DoesNotExist:
        raise Http404("Asset does not exist")

    filepath = os.path.join(settings.LD_ASSET_FOLDER, asset.file)

    if not os.path.exists(filepath):
        raise Http404("Asset does not exist")

    if asset.gzip:
        with gzip.open(filepath, "rb") as f:
            content = f.read()
    else:
        with open(filepath, "rb") as f:
            content = f.read()

    return HttpResponse(content, content_type=asset.content_type)
