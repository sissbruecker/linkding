import re

import bleach
import markdown
from bleach.linkifier import DEFAULT_CALLBACKS, Linker
from bleach_allowlist import markdown_attrs, markdown_tags
from django import template
from django.utils.safestring import mark_safe

from bookmarks import utils
from bookmarks.widgets import FormCheckbox

register = template.Library()


@register.simple_tag(takes_context=True)
def update_query_string(context, **kwargs):
    query = context.request.GET.copy()

    # Replace query params with the ones from tag parameters
    for key in kwargs:
        query.__setitem__(key, kwargs[key])

    return query.urlencode()


@register.simple_tag(takes_context=True)
def replace_query_param(context, **kwargs):
    query = context.request.GET.copy()

    # Create query param or replace existing
    for key in kwargs:
        value = kwargs[key]
        query.__setitem__(key, value)

    return query.urlencode()


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


def schemeless_urls_to_https(attrs, _new):
    href_key = (None, "href")
    if href_key not in attrs:
        return attrs

    if attrs.get("_text", "").startswith("http://"):
        # The original text explicitly specifies http://, so keep it
        return attrs

    attrs[href_key] = re.sub(r"^http://", "https://", attrs[href_key])
    return attrs


linker = Linker(callbacks=[*DEFAULT_CALLBACKS, schemeless_urls_to_https])


@register.simple_tag(name="markdown", takes_context=True)
def render_markdown(context, markdown_text):
    # naive approach to reusing the renderer for a single request
    # works for bookmark list for now
    if "markdown_renderer" not in context:
        renderer = markdown.Markdown(extensions=["fenced_code", "nl2br"])
        context["markdown_renderer"] = renderer
    else:
        renderer = context["markdown_renderer"]

    as_html = renderer.convert(markdown_text)
    sanitized_html = bleach.clean(as_html, markdown_tags, markdown_attrs)
    linkified_html = linker.linkify(sanitized_html)

    return mark_safe(linkified_html)


def append_attr(widget, attr, value):
    attrs = widget.attrs
    if attrs.get(attr):
        attrs[attr] += " " + value
    else:
        attrs[attr] = value


@register.simple_tag
def formlabel(field, label_text):
    return mark_safe(
        f'<label for="{field.id_for_label}" class="form-label">{label_text}</label>'
    )


@register.simple_tag
def formfield(field, **kwargs):
    widget = field.field.widget

    label = kwargs.pop("label", None)
    if label and isinstance(widget, FormCheckbox):
        widget.label = label

    if kwargs.pop("has_help", False):
        append_attr(widget, "aria-describedby", field.auto_id + "_help")

    has_errors = hasattr(field, "errors") and field.errors
    if has_errors:
        append_attr(widget, "class", "is-error")
        append_attr(widget, "aria-describedby", field.auto_id + "_error")
    if field.field.required and not has_errors:
        append_attr(widget, "aria-invalid", "false")

    for attr, value in kwargs.items():
        attr = attr.replace("_", "-")
        if attr == "class":
            append_attr(widget, "class", value)
        else:
            widget.attrs[attr] = value

    return field.as_widget()


@register.tag
def formhelp(parser, token):
    try:
        tag_name, field_var = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            f"{token.contents.split()[0]!r} tag requires a single argument (form field)"
        ) from None
    nodelist = parser.parse(("endformhelp",))
    parser.delete_first_token()
    return FormHelpNode(nodelist, field_var)


class FormHelpNode(template.Node):
    def __init__(self, nodelist, field_var):
        self.nodelist = nodelist
        self.field_var = template.Variable(field_var)

    def render(self, context):
        field = self.field_var.resolve(context)
        content = self.nodelist.render(context)
        return f'<div id="{field.auto_id}_help" class="form-input-hint">{content}</div>'
