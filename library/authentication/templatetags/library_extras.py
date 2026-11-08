from django import template

register = template.Library()


@register.filter
def cover(book_id):
    """CSS class with one of six cover colours for a book."""
    try:
        return f'cover-{int(book_id) % 6}'
    except (TypeError, ValueError):
        return 'cover-0'


@register.filter
def initial(value):
    """First letter of a string in upper case (used for avatars)."""
    return (str(value or '?')[:1]).upper()


@register.simple_tag(takes_context=True)
def query_with(context, **kwargs):
    """Current GET query string with some parameters replaced."""
    params = context['request'].GET.copy()
    for key, value in kwargs.items():
        if value in ('', None):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f'?{encoded}' if encoded else '?'
