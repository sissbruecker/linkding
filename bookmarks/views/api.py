from django.http import JsonResponse

from services.website_loader import load_website_metadata


def website_metadata(request):
    url = request.GET.get('url')
    metadata = load_website_metadata(url)
    return JsonResponse(metadata.to_dict())
