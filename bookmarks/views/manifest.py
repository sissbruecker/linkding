from django.http import JsonResponse
from django.conf import settings


def manifest(request):
    response = {
        "short_name": "linkding",
        "start_url": "bookmarks",
        "display": "standalone",
        "scope": "/" + settings.LD_CONTEXT_PATH,
    }

    return JsonResponse(response, status=200)
