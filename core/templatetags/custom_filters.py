from django import template
import re
from django.utils.html import escape

register = template.Library()
#
# @register.filter(name='highlight_alt')
# def highlight_alt(value):
#     if not isinstance(value, str):
#         return value
#
#     value = escape(value)  # escape the whole thing
#     # highlight only the alt attribute in the escaped string
#     return re.sub(
#         r'(alt=&quot;Description of the image&quot;)',
#         r'<mark>\1</mark>',
#         value
#     )
@register.filter(name='highlight_alt')
def highlight_alt(value):
    if not isinstance(value, str):
        return value

    value = escape(value)

    # Match any alt attribute, e.g. alt="anything here"
    return re.sub(
        r'(alt=&quot;[^&]*?&quot;)',
        r'<mark>\1</mark>',
        value
    )



# @register.filter
# def highlight_alt(value):
#     pattern = r'(alt\s*=\s*["\'].*?["\'])'
#     return re.sub(pattern, r'<mark>\1</mark>', value)


@register.filter
def constrain_img(value):
    return re.sub(r'<img([^>]+)>', r'<img\1 style="max-width:100%;max-height:200px;">', value)