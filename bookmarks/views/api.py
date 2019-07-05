from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from bookmarks.services.website_loader import load_website_metadata


@login_required
def api_website_metadata(request):
    url = request.GET.get('url')
    metadata = load_website_metadata(url)
    return JsonResponse(metadata.to_dict())
