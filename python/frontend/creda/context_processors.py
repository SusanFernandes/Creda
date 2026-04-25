"""Template flags — optional features (voice UI off by default)."""
from django.conf import settings


def creda_flags(_request):
    return {"CREDA_VOICE_UI": getattr(settings, "CREDA_VOICE_UI", False)}
