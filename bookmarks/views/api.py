from django.contrib.auth.decorators import login_required
from django.forms import model_to_dict
from django.http import JsonResponse
from django.urls import reverse

from bookmarks.services.website_loader import load_website_metadata
from bookmarks.models import Bookmark


@login_required
def check_url(request):
    url = request.GET.get('url')
    bookmark = Bookmark.objects.filter(owner=request.user, url=url).first()
    existing_bookmark_data = None

    if bookmark is not None:
        existing_bookmark_data = {
            'id': bookmark.id,
            'edit_url': reverse('bookmarks:edit', args=[bookmark.id])
        }

    metadata = load_website_metadata(url)

    return JsonResponse({
        'bookmark': existing_bookmark_data,
        'metadata': metadata.to_dict()
    })
