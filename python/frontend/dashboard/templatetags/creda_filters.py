"""Custom template filters for CREDA dashboard."""
import json
import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="strip_markdown")
def strip_markdown(value):
    """Strip markdown bold/italic markers from LLM output."""
    if not value:
        return value
    text = str(value)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # **bold**
    text = re.sub(r"\*(.+?)\*", r"\1", text)       # *italic*
    text = re.sub(r"__(.+?)__", r"\1", text)        # __bold__
    text = re.sub(r"_(.+?)_", r"\1", text)          # _italic_
    return text


@register.filter(name="indian_number")
def indian_number(value):
    """Format number with Indian comma system (12,34,567)."""
    try:
        num = int(float(value))
    except (ValueError, TypeError):
        return value
    if num < 0:
        return "-" + indian_number(-num)
    s = str(num)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    # Add commas every 2 digits for the rest
    parts = []
    while rest:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(parts) + "," + last3


@register.filter(name="humanize_key")
def humanize_key(value):
    """Convert snake_case keys to Title Case: 'emergency_preparedness' → 'Emergency Preparedness'."""
    if not value:
        return value
    return str(value).replace("_", " ").title()


@register.filter(name="to_json")
def to_json(value):
    """Safely convert Python dict to JSON for use in <script> blocks."""
    try:
        return mark_safe(json.dumps(value))
    except (TypeError, ValueError):
        return "{}"
