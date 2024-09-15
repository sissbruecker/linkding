from django.http import HttpRequest, HttpResponse
from django.shortcuts import render as django_render


def accept(request):
    return "text/vnd.turbo-stream.html" in request.headers.get("Accept", "")


def render(request: HttpRequest, template_name: str, context: dict) -> HttpResponse:
    response = django_render(request, template_name, context)
    response["Content-Type"] = "text/vnd.turbo-stream.html"
    return response
