"""3-step onboarding wizard — session step counter; persists via FastAPI PATCH/POST /profile/upsert."""

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

logger = logging.getLogger("creda.onboarding")


@login_required
async def onboarding_wizard_view(request):
    request.session.setdefault("onboarding_step", 1)
    step = int(request.session.get("onboarding_step", 1))
    meta = {"step": step, "total": 3}
    try:
        from creda.middleware import _fastapi_user_id_for_request

        uid = _fastapi_user_id_for_request(request) or str(request.user.id)
        profile = await request.backend.get_profile(uid)
        meta["profile"] = profile
    except Exception:
        meta["profile"] = {}
    return render(request, "onboarding/wizard.html", meta)


@login_required
async def onboarding_save_step_view(request, step_number: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        import json

        body = json.loads(request.body or b"{}")
    except Exception:
        body = {}

    try:
        await request.backend.upsert_profile(body)
        request.session["onboarding_step"] = min(step_number + 1, 4)
        if step_number >= 3:
            await request.backend.upsert_profile({"onboarding_complete": True})
            request.session.pop("onboarding_step", None)
            request.session["show_first_report_banner"] = True
            return JsonResponse({"ok": True, "done": True, "redirect": "/dashboard/"})
    except Exception as e:
        logger.exception("onboarding save: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
    return JsonResponse({"ok": True, "done": False, "next_step": step_number + 1})


@login_required
def onboarding_resume_view(request):
    request.session["onboarding_step"] = 1
    return redirect("onboarding_wizard")
