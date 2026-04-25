"""3-step onboarding wizard — URL steps + session; persists via FastAPI /profile/upsert."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

logger = logging.getLogger("creda.onboarding")


def _normalize_onboarding_payload(body: dict) -> dict:
    raw = {k: v for k, v in body.items() if v is not None and v != ""}
    for k, v in list(raw.items()):
        if v == "on":
            raw[k] = True
    et = raw.get("employment_type")
    if et == "self_employed":
        raw["employment_type"] = "self-employed"
    if raw.get("risk_tolerance"):
        raw["risk_appetite"] = raw["risk_tolerance"]
    for bk in (
        "has_nps", "parents_age_above_60", "has_health_insurance", "has_home_loan",
        "pays_rent", "health_cover_parents", "is_metro",
    ):
        if bk in raw and isinstance(raw[bk], str):
            raw[bk] = raw[bk].lower() in ("true", "1", "yes", "on")
    if isinstance(raw.get("sector_interests"), list):
        raw["sector_interests"] = json.dumps(raw["sector_interests"])
    if isinstance(raw.get("alert_types"), list):
        raw["alert_types"] = json.dumps(raw["alert_types"])
    fx = raw.get("monthly_fixed_expenses")
    vx = raw.get("monthly_variable_expenses")
    if fx is not None and vx is not None:
        try:
            if not raw.get("monthly_expenses"):
                raw["monthly_expenses"] = float(fx) + float(vx)
        except (TypeError, ValueError):
            pass
    raw.pop("health_cover_parents", None)
    raw.pop("pays_rent", None)
    return raw


@login_required
async def onboarding_wizard_view(request):
    request.session.setdefault("onboarding_step", 1)
    step = int(request.session.get("onboarding_step", 1))
    step = max(1, min(step, 3))
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
async def onboarding_step_view(request, step_number: int):
    if step_number < 1 or step_number > 3:
        return redirect("onboarding_wizard")
    request.session["onboarding_step"] = step_number
    return await onboarding_wizard_view(request)


@login_required
async def onboarding_save_step_view(request, step_number: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        body = json.loads(request.body or b"{}")
    except Exception:
        body = {}

    body = _normalize_onboarding_payload(body)

    try:
        await request.backend.upsert_profile(body)
        if step_number >= 3:
            await request.backend.upsert_profile({"onboarding_complete": True})
            request.session.pop("onboarding_step", None)
            request.session["show_first_report_banner"] = True
            return JsonResponse({"ok": True, "done": True, "redirect": "/dashboard/"})
        request.session["onboarding_step"] = step_number + 1
    except Exception as e:
        logger.exception("onboarding save: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
    return JsonResponse({"ok": True, "done": False, "next_step": step_number + 1})


@login_required
def onboarding_resume_view(request):
    request.session["onboarding_step"] = 1
    return redirect("onboarding_step", step_number=1)
