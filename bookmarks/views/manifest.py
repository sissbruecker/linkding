from django.http import JsonResponse
from django.conf import settings


def manifest(request):
    response = {
        "short_name": "linkding",
        "name": "linkding",
        "description": "Self-hosted bookmark service",
        "start_url": "bookmarks",
        "display": "standalone",
        "scope": "/" + settings.LD_CONTEXT_PATH,
        "theme_color": "#5856e0",
        "background_color": (
            "#161822" if request.user_profile.theme == "dark" else "#ffffff"
        ),
        "icons": [
            {
                "src": "/" + settings.LD_CONTEXT_PATH + "static/logo.svg",
                "type": "image/svg+xml",
                "sizes": "512x512",
                "purpose": "any",
            },
            {
                "src": "/" + settings.LD_CONTEXT_PATH + "static/logo-512.png",
                "type": "image/png",
                "sizes": "512x512",
                "purpose": "any",
            },
            {
                "src": "/" + settings.LD_CONTEXT_PATH + "static/logo-192.png",
                "type": "image/png",
                "sizes": "192x192",
                "purpose": "any",
            },
            {
                "src": "/" + settings.LD_CONTEXT_PATH + "static/maskable-logo.svg",
                "type": "image/svg+xml",
                "sizes": "512x512",
                "purpose": "maskable",
            },
            {
                "src": "/" + settings.LD_CONTEXT_PATH + "static/maskable-logo-512.png",
                "type": "image/png",
                "sizes": "512x512",
                "purpose": "maskable",
            },
            {
                "src": "/" + settings.LD_CONTEXT_PATH + "static/maskable-logo-192.png",
                "type": "image/png",
                "sizes": "192x192",
                "purpose": "maskable",
            },
        ],
        "shortcuts": [
            {
                "name": "Add bookmark",
                "url": "/" + settings.LD_CONTEXT_PATH + "bookmarks/new",
            },
            {
                "name": "Archived",
                "url": "/" + settings.LD_CONTEXT_PATH + "bookmarks/archived",
            },
            {
                "name": "Unread",
                "url": "/" + settings.LD_CONTEXT_PATH + "bookmarks?unread=yes",
            },
            {
                "name": "Untagged",
                "url": "/" + settings.LD_CONTEXT_PATH + "bookmarks?q=!untagged",
            },
            {
                "name": "Shared",
                "url": "/" + settings.LD_CONTEXT_PATH + "bookmarks/shared",
            },
        ],
        "screenshots": [
            {
                "src": "/"
                + settings.LD_CONTEXT_PATH
                + "static/linkding-screenshot.png",
                "type": "image/png",
                "sizes": "2158x1160",
                "form_factor": "wide",
            }
        ],
        "share_target": {
            "action": "/" + settings.LD_CONTEXT_PATH + "bookmarks/new",
            "method": "GET",
            "enctype": "application/x-www-form-urlencoded",
            "params": {
                "url": "url",
                "text": "url",
                "title": "title",
            },
        },
    }

    return JsonResponse(response, status=200)
