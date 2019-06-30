from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def update_query_string(context, **kwargs):
    query = context.request.GET.copy()

    # Replace query params with the ones from tag parameters
    for key in kwargs:
        query.__setitem__(key, kwargs[key])

    return query.urlencode()


@register.simple_tag(takes_context=True)
def append_query_param(context, **kwargs):
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
