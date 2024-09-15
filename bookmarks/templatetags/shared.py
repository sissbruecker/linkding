import re

import bleach
import markdown
from bleach_allowlist import markdown_tags, markdown_attrs
from django import template
from django.utils.safestring import mark_safe

from bookmarks import utils
from bookmarks.models import UserProfile

register = template.Library()


@register.simple_tag(takes_context=True)
def update_query_string(context, **kwargs):
    query = context.request.GET.copy()

    # Replace query params with the ones from tag parameters
    for key in kwargs:
        query.__setitem__(key, kwargs[key])

    return query.urlencode()


@register.simple_tag(takes_context=True)
def add_tag_to_query(context, tag_name: str):
    params = context.request.GET.copy()

    # Append to or create query string
    query_string = params.get("q", "")
    query_string = (query_string + " #" + tag_name).strip()
    params.setlist("q", [query_string])

    # Remove details ID and page number
    params.pop("details", None)
    params.pop("page", None)

    return params.urlencode()


@register.simple_tag(takes_context=True)
def remove_tag_from_query(context, tag_name: str):
    params = context.request.GET.copy()
    if params.__contains__("q"):
        # Split query string into parts
        query_string = params.__getitem__("q")
        query_parts = query_string.split()
        # Remove tag with hash
        tag_name_with_hash = "#" + tag_name
        query_parts = [
            part
            for part in query_parts
            if str.lower(part) != str.lower(tag_name_with_hash)
        ]
        # When using lax tag search, also remove tag without hash
        profile = context.request.user_profile
        if profile.tag_search == UserProfile.TAG_SEARCH_LAX:
            query_parts = [
                part for part in query_parts if str.lower(part) != str.lower(tag_name)
            ]
        # Rebuild query string
        query_string = " ".join(query_parts)
        params.__setitem__("q", query_string)

    # Remove details ID and page number
    params.pop("details", None)
    params.pop("page", None)

    return params.urlencode()


@register.simple_tag(takes_context=True)
def replace_query_param(context, **kwargs):
    query = context.request.GET.copy()

    # Create query param or replace existing
    for key in kwargs:
        value = kwargs[key]
        query.__setitem__(key, value)

    return query.urlencode()


@register.filter(name="hash_tag")
def hash_tag(tag_name):
    return "#" + tag_name


@register.filter(name="first_char")
def first_char(text):
    return text[0]


@register.filter(name="remaining_chars")
def remaining_chars(text, index):
    return text[index:]


@register.filter(name="humanize_absolute_date")
def humanize_absolute_date(value):
    if value in (None, ""):
        return ""
    return utils.humanize_absolute_date(value)


@register.filter(name="humanize_relative_date")
def humanize_relative_date(value):
    if value in (None, ""):
        return ""
    return utils.humanize_relative_date(value)


@register.tag
def htmlmin(parser, token):
    nodelist = parser.parse(("endhtmlmin",))
    parser.delete_first_token()
    return HtmlMinNode(nodelist)


class HtmlMinNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)

        output = re.sub(r"\s+", " ", output)

        return output


@register.simple_tag(name="markdown", takes_context=True)
def render_markdown(context, markdown_text):
    # naive approach to reusing the renderer for a single request
    # works for bookmark list for now
    if not ("markdown_renderer" in context):
        renderer = markdown.Markdown(extensions=["fenced_code", "nl2br"])
        context["markdown_renderer"] = renderer
    else:
        renderer = context["markdown_renderer"]

    as_html = renderer.convert(markdown_text)
    sanitized_html = bleach.clean(as_html, markdown_tags, markdown_attrs)

    return mark_safe(sanitized_html)
