from django.http import HttpRequest, HttpResponse
from django.template import loader


def accept(request: HttpRequest):
    is_turbo_request = "text/vnd.turbo-stream.html" in request.headers.get("Accept", "")
    disable_turbo = request.POST.get("disable_turbo", "false") == "true"

    return is_turbo_request and not disable_turbo


def is_frame(request: HttpRequest, frame: str) -> bool:
    return request.headers.get("Turbo-Frame") == frame


def frame(request: HttpRequest, template_name: str, context: dict) -> HttpResponse:
    """
    Renders the specified template into an HTML skeleton including <head> with
    respective metadata. The template should only contain a frame. Used for
    Turbo Frame requests that modify the top frame's URL.
    """
    html = loader.render_to_string("shared/top_frame.html", context, request)
    content = loader.render_to_string(template_name, context, request)
    html = html.replace("<!--content-->", content)
    response = HttpResponse(html, status=200)
    return response


def update(
    request: HttpRequest,
    target: str,
    template_name: str,
    context: dict,
    method: str | None = "",
) -> str:
    """Render a template wrapped in an update turbo-stream element."""
    content = loader.render_to_string(template_name, context, request)
    method_attr = f' method="{method}"' if method else ""
    return f'<turbo-stream action="update"{method_attr} target="{target}"><template>{content}</template></turbo-stream>'


def replace(
    request: HttpRequest,
    target: str,
    template_name: str,
    context: dict,
    method: str | None = "",
) -> str:
    """Render a template wrapped in a replace turbo-stream element."""
    content = loader.render_to_string(template_name, context, request)
    method_attr = f' method="{method}"' if method else ""
    return f'<turbo-stream action="replace"{method_attr} target="{target}"><template>{content}</template></turbo-stream>'


def stream(*streams: str) -> HttpResponse:
    """Combine multiple stream elements into a turbo-stream response."""
    return HttpResponse(
        "\n".join(streams),
        status=200,
        content_type="text/vnd.turbo-stream.html",
    )
