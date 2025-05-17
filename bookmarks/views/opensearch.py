from django.urls import reverse
from django.shortcuts import render


def opensearch(request):
    base_url = request.build_absolute_uri(reverse("linkding:root"))
    bookmarks_url = request.build_absolute_uri(reverse("linkding:bookmarks.index"))

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
