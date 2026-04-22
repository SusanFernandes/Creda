"""
Dashboard views — all async.
Each view calls FastAPI via request.backend (BackendClient) without blocking.
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect

logger = logging.getLogger("creda.dashboard")


@login_required
async def dashboard_view(request):
    """Main dashboard — summary cards, nudges, quick actions."""
    try:
        profile = await request.backend.get_profile(str(request.user.id))
        nudges = await request.backend.get_nudges()
    except Exception:
        profile = None
        nudges = []

    # Redirect to onboarding if profile incomplete
    if not profile or not profile.get("onboarding_complete"):
        return redirect("onboarding")

    return render(request, "dashboard/dashboard.html", {
        "profile": profile,
        "nudges": nudges,
    })


@login_required
async def chat_view(request):
    """Chat interface — HTMX SSE streaming."""
    return render(request, "dashboard/chat.html")


@login_required
async def portfolio_view(request):
    """Portfolio overview + CAMS upload."""
    try:
        summary = await request.backend.get_portfolio_summary()
    except Exception:
        summary = None
    return render(request, "dashboard/portfolio.html", {"portfolio": summary})


@login_required
async def portfolio_upload(request):
    """Handle CAMS PDF upload (HTMX)."""
    if request.method != "POST":
        return render(request, "dashboard/partials/upload_result.html", {"error": "Invalid method"})

    file = request.FILES.get("file")
    if not file:
        return render(request, "dashboard/partials/upload_result.html", {"error": "No file selected"})

    password = request.POST.get("password", "")
    try:
        result = await request.backend.upload_portfolio(file.read(), file.name, password)
        return render(request, "dashboard/partials/upload_result.html", {"result": result})
    except Exception as e:
        return render(request, "dashboard/partials/upload_result.html", {"error": str(e)})


@login_required
async def health_view(request):
    """Money Health Score page."""
    try:
        result = await request.backend.money_health()
    except Exception:
        result = None
    return render(request, "dashboard/health.html", {"health": result})


@login_required
async def fire_view(request):
    """FIRE Planner page."""
    try:
        result = await request.backend.fire_planner()
    except Exception:
        result = None
    return render(request, "dashboard/fire.html", {"fire": result})


@login_required
async def tax_view(request):
    """Tax Wizard page."""
    try:
        result = await request.backend.tax_wizard()
    except Exception:
        result = None
    return render(request, "dashboard/tax.html", {"tax": result})


@login_required
async def budget_view(request):
    """Budget Coach page."""
    try:
        result = await request.backend.budget_coach()
    except Exception:
        result = None
    return render(request, "dashboard/budget.html", {"budget": result})


@login_required
async def goals_view(request):
    """Goal Planner page."""
    try:
        result = await request.backend.goal_planner()
    except Exception:
        result = None
    return render(request, "dashboard/goals.html", {"goals": result})


@login_required
async def stress_test_view(request):
    """Stress Test page."""
    events = request.GET.getlist("events") or ["market_crash_30", "baby", "job_loss"]
    try:
        result = await request.backend.stress_test(events)
    except Exception:
        result = None
    return render(request, "dashboard/stress_test.html", {"stress": result, "events": events})


@login_required
async def settings_view(request):
    """User settings page."""
    if request.method == "POST":
        data = {}
        for key in ("name", "age", "monthly_income", "monthly_expenses", "language",
                     "risk_appetite", "employment_type", "city"):
            val = request.POST.get(key)
            if val is not None and val != "":
                if key in ("age",):
                    data[key] = int(val)
                elif key in ("monthly_income", "monthly_expenses"):
                    data[key] = float(val)
                else:
                    data[key] = val
        try:
            await request.backend.upsert_profile(data)
        except Exception as e:
            logger.error("Settings update error: %s", e)

    try:
        profile = await request.backend.get_profile(str(request.user.id))
    except Exception:
        profile = None
    return render(request, "dashboard/settings.html", {"profile": profile})


@login_required
async def onboarding_view(request):
    """Onboarding flow for new users."""
    return render(request, "dashboard/onboarding.html")


@login_required
async def notifications_view(request):
    """All notifications / nudges."""
    try:
        nudges = await request.backend.get_nudges()
    except Exception:
        nudges = []
    return render(request, "dashboard/notifications.html", {"nudges": nudges})


# ── New ET-Inspired Views ──────────────────────────────────────────


@login_required
async def couples_view(request):
    """Couples Finance page."""
    result = None
    if request.method == "POST":
        try:
            partner_income = float(request.POST.get("partner_income", 0))
            partner_expenses = float(request.POST.get("partner_expenses", 0))
            result = await request.backend.couples_finance(partner_income, partner_expenses)
        except Exception as e:
            logger.error("Couples finance error: %s", e)
    return render(request, "dashboard/couples.html", {"couples": result})


@login_required
async def sip_calculator_view(request):
    """SIP Calculator page."""
    try:
        result = await request.backend.sip_calculator()
    except Exception:
        result = None
    return render(request, "dashboard/sip_calculator.html", {"sip": result})


@login_required
async def market_pulse_view(request):
    """Market Pulse — real-time market intelligence."""
    try:
        result = await request.backend.market_pulse()
    except Exception as e:
        logger.error("Market pulse error: %s", e)
        result = None
    return render(request, "dashboard/market_pulse.html", {"market": result})


@login_required
async def tax_copilot_view(request):
    """Tax Copilot — year-round tax optimization."""
    try:
        result = await request.backend.tax_copilot()
    except Exception:
        result = None
    return render(request, "dashboard/tax_copilot.html", {"tax_copilot": result})


@login_required
async def money_personality_view(request):
    """Money Personality assessment."""
    try:
        result = await request.backend.money_personality()
    except Exception:
        result = None
    return render(request, "dashboard/money_personality.html", {"personality": result})


@login_required
async def goal_simulator_view(request):
    """Goal Simulator — what-if scenario modeling."""
    result = None
    target = float(request.GET.get("target", 5000000))
    years = int(request.GET.get("years", 10))
    try:
        result = await request.backend.goal_simulator(target, years)
    except Exception as e:
        logger.error("Goal simulator error: %s", e)
    return render(request, "dashboard/goal_simulator.html", {"sim": result, "target": target, "years": years})


@login_required
async def social_proof_view(request):
    """Social Proof — peer benchmarking."""
    try:
        result = await request.backend.social_proof()
    except Exception:
        result = None
    return render(request, "dashboard/social_proof.html", {"social": result})


@login_required
async def research_view(request):
    """ET Research — deep financial research."""
    result = None
    query = request.GET.get("q", "")
    if query:
        try:
            result = await request.backend.et_research(query)
        except Exception:
            pass
    return render(request, "dashboard/research.html", {"research": result, "query": query})


@login_required
async def voice_view(request):
    """Voice Agent interface."""
    return render(request, "dashboard/voice.html")


@login_required
async def advisor_view(request):
    """Human Advisor handoff page."""
    try:
        result = await request.backend.human_handoff()
    except Exception:
        result = None
    return render(request, "dashboard/advisor.html", {"handoff": result})


@login_required
async def compliance_view(request):
    """SEBI Compliance — advice audit trail and AI disclosure."""
    report = None
    disclosure = None
    try:
        disclosure = await request.backend.ai_disclosure()
    except Exception:
        pass
    if request.method == "POST":
        start = request.POST.get("start_date", "")
        end = request.POST.get("end_date", "")
        try:
            report = await request.backend.compliance_report(start, end)
        except Exception as e:
            logger.error("Compliance report error: %s", e)
    return render(request, "dashboard/compliance.html", {
        "report": report, "disclosure": disclosure,
    })


@login_required
async def family_view(request):
    """Family Wealth — household financial aggregation."""
    members = []
    wealth = None
    try:
        members_data = await request.backend.family_members()
        members = members_data.get("members", [])
    except Exception:
        pass

    if request.method == "POST" and request.POST.get("action") == "link":
        email = request.POST.get("member_email", "")
        relationship = request.POST.get("relationship", "spouse")
        if email:
            try:
                await request.backend.link_family_member(email, relationship)
            except Exception as e:
                logger.error("Family link error: %s", e)
            # Refresh members
            try:
                members_data = await request.backend.family_members()
                members = members_data.get("members", [])
            except Exception:
                pass

    try:
        wealth = await request.backend.family_wealth()
    except Exception as e:
        logger.error("Family wealth error: %s", e)

    return render(request, "dashboard/family.html", {
        "members": members, "wealth": wealth,
    })


# ── API Proxy Endpoints ────────────────────────────────────────────


@login_required
async def api_profile_upsert(request):
    """Proxy POST to FastAPI /profile/upsert — used by onboarding form."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        result = await request.backend.upsert_profile(data)
        return JsonResponse(result)
    except Exception as e:
        logger.error("Profile upsert proxy error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_chat(request):
    """Proxy POST to FastAPI /chat — used by chat interface."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        result = await request.backend.post_chat(
            message=data.get("message", ""),
            session_id=data.get("session_id", ""),
            language=data.get("language", "en"),
            voice_mode=data.get("voice_mode", False),
        )
        return JsonResponse(result)
    except Exception as e:
        logger.error("Chat proxy error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_voice(request):
    """Proxy POST to FastAPI /voice — used by voice interface."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        # Voice sends form data with audio file
        audio = request.FILES.get("audio")
        language = request.POST.get("language", "en")
        if audio:
            audio_bytes = audio.read()
            result = await request.backend.voice_chat(audio_bytes, audio.name, language)
        else:
            data = json.loads(request.body)
            result = await request.backend.post_chat(
                message=data.get("message", ""),
                language=data.get("language", "en"),
                voice_mode=True,
            )
        return JsonResponse(result)
    except Exception as e:
        logger.error("Voice proxy error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_nudge_read(request, nudge_id):
    """Proxy POST to mark a single nudge as read."""
    try:
        result = await request.backend.mark_nudge_read(nudge_id)
        return JsonResponse(result)
    except Exception as e:
        logger.error("Nudge read proxy error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_nudge_mark_all_read(request):
    """Proxy POST to mark all nudges as read."""
    try:
        nudges = await request.backend.get_nudges()
        for nudge in nudges:
            await request.backend.mark_nudge_read(nudge.get("id", ""))
        return JsonResponse({"status": "ok"})
    except Exception as e:
        logger.error("Nudge mark-all-read proxy error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)
