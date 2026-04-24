"""
Dashboard views — all async.
Each view calls FastAPI via request.backend (BackendClient) without blocking.
"""
import json
import logging

from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect

from creda.middleware import _fastapi_user_id_for_request

logger = logging.getLogger("creda.dashboard")

# Multipart/POST body: parse in a thread so async views see FILES/body (Django ASGI).
@sync_to_async
def _parse_api_voice_request(request):
    f = request.FILES.get("audio")
    if f:
        return ("m", f.read(), f.name, request.POST.get("language", "en"))
    return ("j", json.loads((request.body or b"{}").decode() or "{}"))


@sync_to_async
def _parse_voice_navigate_request(request):
    f = request.FILES.get("audio")
    if not f:
        return b"", "en", ""
    return f.read(), request.POST.get("language", "en"), f.name


def _fastapi_user_id(request) -> str:
    """FastAPI users.id (UUID); JWT/session from middleware helper, else Django pk."""
    uid = _fastapi_user_id_for_request(request)
    return uid if uid else str(request.user.id)


@login_required
async def dashboard_view(request):
    """Main dashboard — summary cards, nudges, quick actions, health preview."""
    try:
        profile = await request.backend.get_profile(_fastapi_user_id(request))
    except Exception:
        profile = None

    # Redirect to onboarding if profile incomplete
    if not profile or not profile.get("onboarding_complete"):
        return redirect("onboarding")

    # Generate dynamic nudges if none exist, then fetch
    try:
        await request.backend.generate_nudges()
    except Exception:
        pass
    try:
        nudges = await request.backend.get_nudges()
    except Exception:
        nudges = []

    # Fetch health score preview for dashboard widget
    health = None
    try:
        health = await request.backend.money_health()
    except Exception:
        pass

    # Fetch portfolio summary for dashboard
    portfolio = None
    try:
        portfolio = await request.backend.get_portfolio_summary()
    except Exception:
        pass

    return render(request, "dashboard/dashboard.html", {
        "profile": profile,
        "nudges": nudges,
        "health": health,
        "portfolio": portfolio,
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
async def portfolio_xray_view(request):
    """Run X-Ray analysis on portfolio (HTMX partial)."""
    try:
        result = await request.backend.run_xray()
    except Exception as e:
        return render(request, "dashboard/partials/xray_result.html", {"error": str(e)})
    return render(request, "dashboard/partials/xray_result.html", {"xray": result})


@login_required
async def portfolio_refresh_navs(request):
    """Refresh NAVs for all holdings (HTMX partial)."""
    try:
        result = await request.backend.refresh_navs()
    except Exception as e:
        return render(request, "dashboard/partials/refresh_result.html", {"error": str(e)})
    return render(request, "dashboard/partials/refresh_result.html", {"result": result})


@login_required
async def health_view(request):
    """Money Health Score page — shows skeleton immediately, content loads via HTMX."""
    return render(request, "dashboard/health.html", {"health": None, "deferred": True})


@login_required
async def health_htmx(request):
    """HTMX fragment — actual health score data."""
    try:
        result = await request.backend.money_health()
    except Exception:
        result = None
    return render(request, "dashboard/partials/health_content.html", {"health": result})


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
    """Tax Wizard page — merged with Tax Copilot (tabs)."""
    tax_result = None
    copilot_result = None
    active_tab = request.GET.get("tab", "regime")
    try:
        tax_result = await request.backend.tax_wizard()
    except Exception:
        pass
    try:
        copilot_result = await request.backend.tax_copilot()
    except Exception:
        pass
    return render(request, "dashboard/tax.html", {
        "tax": tax_result,
        "tax_copilot": copilot_result,
        "active_tab": active_tab,
    })


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
    """Goal Planner page — merged with Goal Simulator (tabs)."""
    goals_result = None
    sim_result = None
    active_tab = request.GET.get("tab", "goals")
    sim_target = float(request.GET.get("target", 5000000))
    sim_years = int(request.GET.get("years", 10))
    try:
        goals_result = await request.backend.goal_planner()
    except Exception:
        pass
    # Fetch simulator data if on simulator tab or if target/years were submitted
    if active_tab == "simulator" or "target" in request.GET:
        try:
            sim_result = await request.backend.goal_simulator(sim_target, sim_years)
        except Exception as e:
            logger.error("Goal simulator error: %s", e)
    return render(request, "dashboard/goals.html", {
        "goals": goals_result,
        "sim": sim_result,
        "active_tab": active_tab,
        "sim_target": int(sim_target),
        "sim_years": sim_years,
    })


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
    settings_error = None
    settings_saved = False

    if request.method == "POST":
        data = {}
        for key in (
            "name", "age", "monthly_income", "monthly_expenses", "language",
            "risk_appetite", "employment_type", "city", "emergency_fund", "monthly_emi",
            "hra", "rent_paid", "fire_target_age", "investments_80c", "nps_contribution",
            "health_insurance_premium", "epf_balance", "nps_balance", "ppf_balance",
        ):
            val = request.POST.get(key)
            if val is not None and val != "":
                if key in ("age", "fire_target_age"):
                    data[key] = int(val)
                elif key in (
                    "monthly_income", "monthly_expenses", "emergency_fund", "monthly_emi",
                    "hra", "rent_paid", "investments_80c", "nps_contribution",
                    "health_insurance_premium", "epf_balance", "nps_balance", "ppf_balance",
                ):
                    data[key] = float(val)
                else:
                    data[key] = val
        if "has_health_insurance" in request.POST:
            data["has_health_insurance"] = request.POST.get("has_health_insurance") == "on"
        try:
            await request.backend.upsert_profile(data)
            settings_saved = True
        except Exception as e:
            logger.exception("Settings update error: %s", e)
            settings_error = (
                "Could not save to the backend. Ensure FastAPI is running (e.g. port 8001) "
                "and you are still logged in."
            )

        if request.headers.get("HX-Request"):
            if settings_error:
                return HttpResponse(
                    f'<p class="text-sm text-red-600">{settings_error}</p>',
                    status=500,
                )
            return HttpResponse(
                '<p class="text-sm text-emerald-600 font-medium">Saved to your profile.</p>'
            )

    profile_load_error = None
    try:
        profile = await request.backend.get_profile(_fastapi_user_id(request))
    except Exception:
        logger.exception("Settings: could not load profile from backend")
        profile = None
        profile_load_error = (
            "We could not load your saved profile from the server. "
            "Check that the API is running; fields below show your account name where available."
        )
    return render(
        request,
        "dashboard/settings.html",
        {
            "profile": profile or {},
            "settings_error": settings_error,
            "settings_saved": settings_saved,
            "profile_load_error": profile_load_error,
        },
    )


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
    """Couples Finance page — auto-detects linked spouse."""
    result = None
    partner = None
    link_message = ""

    # Handle partner link request
    if request.method == "POST" and request.POST.get("action") == "link_partner":
        partner_email = request.POST.get("partner_email", "").strip()
        if partner_email:
            try:
                await request.backend.link_family_member(partner_email, "spouse")
                link_message = f"Link request sent to {partner_email}. They will need to accept it on their account."
            except Exception as e:
                link_message = f"Could not send link request: {e}"

    # Auto-detect linked spouse
    try:
        family = await request.backend.family_members()
        members = family.get("members", [])
        spouse = next((m for m in members if m.get("relationship") == "spouse"), None)
        if spouse:
            partner = spouse
    except Exception:
        pass

    if request.method == "POST" and request.POST.get("action") != "link_partner":
        try:
            partner_income = float(request.POST.get("partner_income", 0))
            partner_expenses = float(request.POST.get("partner_expenses", 0))
            result = await request.backend.couples_finance(partner_income, partner_expenses)
        except Exception as e:
            logger.error("Couples finance error: %s", e)
    return render(request, "dashboard/couples.html", {
        "couples": result, "partner": partner, "link_message": link_message,
    })


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
    """Market Pulse — shows skeleton immediately, content loads via HTMX."""
    return render(request, "dashboard/market_pulse.html", {"market": None, "deferred": True})


@login_required
async def market_pulse_htmx(request):
    """HTMX fragment — actual market pulse data."""
    try:
        result = await request.backend.market_pulse()
    except Exception as e:
        logger.error("Market pulse error: %s", e)
        result = None

    # Transform flat indices dict into list format for template
    if result and result.get("analysis") and isinstance(result["analysis"].get("indices"), dict):
        raw = result["analysis"]["indices"]
        result["analysis"]["indices"] = [
            {"name": "Nifty 50", "value": raw.get("nifty50", 0),
             "change": raw.get("nifty_change", 0), "change_pct": raw.get("nifty_change", 0)},
            {"name": "Sensex", "value": raw.get("sensex", 0),
             "change": raw.get("sensex_change", 0), "change_pct": raw.get("sensex_change", 0)},
        ]

    return render(request, "dashboard/partials/market_pulse_content.html", {"market": result})


@login_required
async def tax_copilot_view(request):
    """Tax Copilot — redirects to merged tax page with copilot tab."""
    return redirect("/tax/?tab=copilot")


@login_required
async def money_personality_view(request):
    """Money Personality assessment."""
    profile = None
    try:
        profile = await request.backend.get_profile(_fastapi_user_id(request))
    except Exception:
        pass
    try:
        result = await request.backend.money_personality()
    except Exception:
        result = None
    return render(
        request,
        "dashboard/money_personality.html",
        {"personality": result, "profile": profile},
    )


@login_required
async def goal_simulator_view(request):
    """Goal Simulator — redirects to merged goals page with simulator tab."""
    target = request.GET.get("target", "5000000")
    years = request.GET.get("years", "10")
    return redirect(f"/goals/?tab=simulator&target={target}&years={years}")


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
async def expense_analytics_view(request):
    """Expense Analytics — smart spending breakdown."""
    try:
        result = await request.backend.expense_analytics()
    except Exception as e:
        logger.error("Expense analytics error: %s", e)
        result = None
    return render(request, "dashboard/expense_analytics.html", {"expense": result})


@login_required
async def advisor_view(request):
    """Human Advisor handoff page."""
    try:
        result = await request.backend.human_handoff()
    except Exception:
        result = None
    return render(request, "dashboard/advisor.html", {"handoff": result})


@login_required
async def life_event_view(request):
    """Life Event Financial Advisor — bonus deployment, marriage planning, etc."""
    result = None
    message = ""
    if request.method == "POST":
        message = request.POST.get("message", "")
        if message:
            try:
                result = await request.backend.life_event_advisor(message)
            except Exception as e:
                logger.error("Life event advisor error: %s", e)
    return render(request, "dashboard/life_events.html", {"result": result, "message": message})


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
        logger.exception("Profile upsert proxy error: %s", e)
        hint = (
            " Ensure the FastAPI backend is running (e.g. make backend) and Postgres is up; "
            "avoid `docker compose down -v` if you want to keep saved profiles."
        )
        return JsonResponse({"error": str(e) + hint}, status=500)


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
async def api_chat_stream(request):
    """SSE streaming proxy — connects to FastAPI /chat/stream and relays SSE to browser."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        import httpx
        from django.conf import settings as django_settings
        data = json.loads(request.body)
        backend_url = django_settings.BACKEND_API_URL.rstrip("/")
        headers = request.backend._headers()

        async def sse_generator():
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{backend_url}/chat/stream",
                    json={
                        "message": data.get("message", ""),
                        "session_id": data.get("session_id", ""),
                        "language": data.get("language", "en"),
                        "voice_mode": data.get("voice_mode", False),
                    },
                    headers=headers,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"

        response = StreamingHttpResponse(
            sse_generator(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
    except Exception as e:
        logger.error("Chat stream error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_voice(request):
    """Proxy POST to FastAPI /voice — used by voice interface."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        parsed = await _parse_api_voice_request(request)
        if parsed[0] == "m":
            _, audio_bytes, name, language = parsed
            result = await request.backend.voice_chat(audio_bytes, name, language)
        else:
            data = parsed[1]
            result = await request.backend.post_chat(
                message=data.get("message", ""),
                language=data.get("language", "en"),
                voice_mode=True,
            )
        return JsonResponse(result)
    except Exception as e:
        logger.error("Voice proxy error: %s", e, exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_voice_navigate(request):
    """Proxy POST to FastAPI /voice/navigate — floating mic hero feature."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        audio_bytes, language, name = await _parse_voice_navigate_request(request)
        if not audio_bytes or not name:
            return JsonResponse({"error": "No audio provided"}, status=400)
        result = await request.backend.voice_navigate(audio_bytes, name, language)
        return JsonResponse(result)
    except Exception as e:
        logger.error("Voice navigate proxy error: %s", e, exc_info=True)
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


@login_required
async def api_export_proxy(request, export_type, fmt):
    """Proxy GET to FastAPI /export/{type}/{fmt} and stream file to browser."""
    import httpx
    from django.conf import settings as django_settings

    backend_url = django_settings.BACKEND_API_URL.rstrip("/")
    headers = request.backend._headers()

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{backend_url}/export/{export_type}/{fmt}",
                headers=headers,
            )
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "application/octet-stream")
            disposition = resp.headers.get("content-disposition", "")

            response = HttpResponse(resp.content, content_type=content_type)
            if disposition:
                response["Content-Disposition"] = disposition
            return response
    except Exception as e:
        logger.error("Export proxy error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def admin_view(request):
    """Admin dashboard — platform stats and activity logs."""
    if not request.user.is_staff:
        return redirect("dashboard")
    try:
        stats = await request.backend.admin_stats()
        activity = await request.backend.admin_activity(limit=30)
        users = await request.backend.admin_users(limit=30)
    except Exception as e:
        logger.error("Admin view error: %s", e)
        stats, activity, users = {}, [], []

    return render(request, "dashboard/admin.html", {
        "stats": stats,
        "activity": activity,
        "users": users,
    })


@login_required
async def report_card_view(request):
    """Financial Report Card — shareable single-page summary."""
    uid = _fastapi_user_id(request)
    profile, health, portfolio, tax = None, None, None, None
    try:
        profile = await request.backend.get_profile(uid)
    except Exception:
        pass
    try:
        health = await request.backend.money_health()
    except Exception:
        pass
    try:
        portfolio = await request.backend.get_portfolio_summary()
    except Exception:
        pass
    try:
        tax = await request.backend.tax_wizard()
    except Exception:
        pass
    return render(request, "dashboard/report_card.html", {
        "profile": profile,
        "health": health,
        "portfolio": portfolio,
        "tax": tax,
    })


@login_required
async def api_budget_expense(request):
    """Proxy POST to FastAPI /budget/expense — log an expense."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        import httpx
        from django.conf import settings as django_settings
        backend_url = django_settings.BACKEND_API_URL.rstrip("/")
        headers = request.backend._headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{backend_url}/budget/expense",
                json=data,
                headers=headers,
            )
            return JsonResponse(resp.json(), status=resp.status_code)
    except Exception as e:
        logger.error("Budget expense proxy error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_goals_create(request):
    """Create a goal via FastAPI POST /portfolio/goals (form POST, then redirect)."""
    if request.method != "POST":
        return redirect("goals")
    name = (request.POST.get("goal_name") or "").strip()
    try:
        amt = float(request.POST.get("target_amount") or 0)
    except ValueError:
        amt = 0.0
    td = (request.POST.get("target_date") or "").strip() or None
    if not name or amt <= 0:
        return redirect("goals")
    try:
        await request.backend.create_goal(name, amt, td if td else None)
    except Exception as e:
        logger.error("Create goal error: %s", e)
    return redirect("goals")


@login_required
async def api_goals_funds(request):
    """Get goals and funds for linking UI."""
    try:
        result = await request.backend.goals_with_funds()
        return JsonResponse(result)
    except Exception as e:
        logger.error("Goals funds error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_link_funds(request):
    """Link portfolio funds to a specific goal."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        result = await request.backend.link_funds_to_goal(
            goal_id=data.get("goal_id", ""),
            fund_ids=data.get("fund_ids", []),
        )
        return JsonResponse(result)
    except Exception as e:
        logger.error("Link funds error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)
