from django import template

from bookmarks import utils

register = template.Library()


@register.simple_tag(takes_context=True)
def update_query_string(context, **kwargs):
    query = context.request.GET.copy()

    # Replace query params with the ones from tag parameters
    for key in kwargs:
        query.__setitem__(key, kwargs[key])

    return query.urlencode()


@register.simple_tag(takes_context=True)
def append_to_query_param(context, **kwargs):
    query = context.request.GET.copy()

    # Append to or create query param
    for key in kwargs:
        if query.__contains__(key):
            value = query.__getitem__(key) + ' '
        else:
            value = ''
        value = value + kwargs[key]
        query.__setitem__(key, value)

    return query.urlencode()


@register.simple_tag(takes_context=True)
def remove_from_query_param(context, **kwargs):
    query = context.request.GET.copy()

    # Remove item from query param
    for key in kwargs:
        if query.__contains__(key):
            value = query.__getitem__(key)
            parts = value.split()
            part_to_remove = kwargs[key]
            updated_parts = [part for part in parts if str.lower(part) != str.lower(part_to_remove)]
            updated_value = ' '.join(updated_parts)
            query.__setitem__(key, updated_value)

    return query.urlencode()

@register.simple_tag(takes_context=True)
def replace_query_param(context, **kwargs):
    query = context.request.GET.copy()

    # Create query param or replace existing
    for key in kwargs:
        value = kwargs[key]
        query.__setitem__(key, value)

    return query.urlencode()


@register.filter(name='hash_tag')
def hash_tag(tag_name):
    return '#' + tag_name


@register.filter(name='first_char')
def first_char(text):
    return text[0]


@register.filter(name='remaining_chars')
def remaining_chars(text, index):
    return text[index:]


@register.filter(name='humanize_absolute_date')
def humanize_absolute_date(value):
    if value in (None, ''):
        return ''
    return utils.humanize_absolute_date(value)


@register.filter(name='humanize_relative_date')
def humanize_relative_date(value):
    if value in (None, ''):
        return ''
    return utils.humanize_relative_date(value)
