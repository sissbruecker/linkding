from django.http import HttpRequest, HttpResponse
from django.shortcuts import render as django_render
from django.template import loader


def accept(request: HttpRequest):
    is_turbo_request = "text/vnd.turbo-stream.html" in request.headers.get("Accept", "")
    disable_turbo = request.POST.get("disable_turbo", "false") == "true"

    return is_turbo_request and not disable_turbo


def is_frame(request: HttpRequest, frame: str) -> bool:
    return request.headers.get("Turbo-Frame") == frame


def stream(request: HttpRequest, template_name: str, context: dict) -> HttpResponse:
    response = django_render(request, template_name, context)
    response["Content-Type"] = "text/vnd.turbo-stream.html"
    return response


def replace(
    request: HttpRequest, target_id: str, template_name: str, context: dict, status=None
) -> HttpResponse:
    """
    Returns a Turbo steam for replacing a specific target with the rendered
    template. Mostly useful for updating forms in place after failed submissions,
    without having to create a separate template.
    """
    if status is None:
        status = 200
    content = loader.render_to_string(template_name, context, request)
    stream_content = f'<turbo-stream action="replace" method="morph" target="{target_id}"><template>{content}</template></turbo-stream>'
    response = HttpResponse(stream_content, status=status)
    response["Content-Type"] = "text/vnd.turbo-stream.html"
    return response
