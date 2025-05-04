from django.db import connections
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import render

def opensearch(request):
    bookmarks_url = request.build_absolute_uri(reverse("linkding:bookmarks.index"))
    base_url = request.build_absolute_uri(reverse("linkding:root"))

    return render(
        request,
        "opensearch.xml",
        {
            "base_url": base_url,
            "bookmarks_url": bookmarks_url,
        },
        content_type="application/opensearchdescription+xml",
        status=200,
    )
