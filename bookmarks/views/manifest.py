from django.http import JsonResponse
from siteroot.settings import LD_CONTEXT_PATH

def manifest(request):
    code = 200
    response = {
        "short_name": "linkding",
        "start_url": "bookmarks",
        "display": "standalone",
        "scope": "/" + LD_CONTEXT_PATH
    }

    return JsonResponse(response, status=code)
