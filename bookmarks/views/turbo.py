from django.http import HttpRequest, HttpResponse
from django.shortcuts import render as django_render


def accept(request):
    is_turbo_request = "text/vnd.turbo-stream.html" in request.headers.get("Accept", "")
    disable_turbo = request.POST.get("disable_turbo", "false") == "true"

    return is_turbo_request and not disable_turbo


def render(request: HttpRequest, template_name: str, context: dict) -> HttpResponse:
    response = django_render(request, template_name, context)
    response["Content-Type"] = "text/vnd.turbo-stream.html"
    return response
