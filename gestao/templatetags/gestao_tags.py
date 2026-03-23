from django import template
import re

register = template.Library()


@register.filter
def extract_field(bloco_text, field_name):
    """Extrai um campo chave:valor de um bloco de texto."""
    if not bloco_text or not field_name:
        return ''
    pattern = rf'{field_name}:\s*(.+)'
    match = re.search(pattern, str(bloco_text), re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ''


@register.filter
def cut(value, arg):
    """Remove uma substring do valor."""
    return value.replace(arg, '')
