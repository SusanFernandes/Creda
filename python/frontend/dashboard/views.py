"""
Dashboard views — all async.
Each view calls FastAPI via request.backend (BackendClient) without blocking.
"""
import asyncio
import json
import logging
from datetime import date

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect

from creda.middleware import _fastapi_user_id_for_request

logger = logging.getLogger("creda.dashboard")


def _invalidate_money_health_cache(request) -> None:
    cache.delete(f"money_health:{_fastapi_user_id(request)}")


def _money_health_response_cacheable(data: dict | None) -> bool:
    """Do not cache incomplete / placeholder money-health payloads."""
    if not isinstance(data, dict):
        return False
    analysis = data.get("analysis")
    if not isinstance(analysis, dict):
        return False
    if analysis.get("profile_incomplete"):
        return False
    if analysis.get("overall_score") is None and not analysis.get("dimensions"):
        return False
    return True

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


def _safe_float(v, default=None):
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _monthly_expenses_total(profile: dict | None) -> float | None:
    if not profile:
        return None
    me = _safe_float(profile.get("monthly_expenses"))
    if me is not None and me > 0:
        return me
    fx = _safe_float(profile.get("monthly_fixed_expenses"), 0.0) or 0.0
    vy = _safe_float(profile.get("monthly_variable_expenses"), 0.0) or 0.0
    s = fx + vy
    return s if s > 0 else None


def _emergency_fund_amount(profile: dict | None) -> float | None:
    if not profile:
        return None
    for key in ("emergency_fund_amount", "emergency_fund"):
        x = _safe_float(profile.get(key))
        if x is not None and x > 0:
            return x
    # Explicit zero: treat as missing for headline (show — per spec)
    z1 = _safe_float(profile.get("emergency_fund_amount"), -1.0)
    z2 = _safe_float(profile.get("emergency_fund"), -1.0)
    if z1 == 0 or z2 == 0:
        return None
    return None


def _compute_dashboard_metrics(profile: dict | None, portfolio: dict | None):
    """Pre-compute headline metrics, display strings, and data_quality hints for the template."""
    out = {
        "net_worth": None,
        "net_worth_note": None,
        "net_worth_dq": "",
        "surplus": None,
        "surplus_note": None,
        "surplus_dq": "",
        "ef_months": None,
        "ef_note": None,
        "ef_dq": "",
        "fire_pct": None,
        "fire_note": None,
        "fire_dq": "",
    }
    if not profile:
        return out

    cams = bool(profile.get("cams_uploaded"))
    pv = _safe_float(portfolio.get("current_value")) if portfolio else None
    if not cams or portfolio is None:
        out["net_worth_note"] = "portfolio_upload"
        pv_display = None
    else:
        pv_display = pv

    epf = _safe_float(profile.get("epf_balance")) or 0.0
    ef = _emergency_fund_amount(profile)
    if pv_display is not None or epf > 0 or (ef is not None):
        nw = (pv_display or 0.0) + epf + (ef or 0.0)
        if nw > 0:
            out["net_worth"] = nw
            if not cams or portfolio is None:
                out["net_worth_dq"] = "partial"
        else:
            out["net_worth"] = None
    else:
        out["net_worth"] = None

    income = _safe_float(profile.get("monthly_income"))
    exp = _monthly_expenses_total(profile)
    emi = _safe_float(profile.get("monthly_emi")) or 0.0
    if income is None or income <= 0 or exp is None or exp <= 0:
        out["surplus_note"] = "income_or_expenses"
    else:
        out["surplus"] = income - exp - emi

    exp2 = exp if (exp is not None and exp > 0) else None
    ef2 = _emergency_fund_amount(profile)
    if ef2 is None:
        out["ef_note"] = "missing_ef"
    elif exp2 is None:
        out["ef_note"] = "missing_expenses"
    else:
        out["ef_months"] = round(ef2 / exp2, 1)

    target = _safe_float(profile.get("fire_corpus_target"))
    corpus_now = _safe_float(portfolio.get("current_value")) if portfolio else None
    if corpus_now is None or corpus_now <= 0:
        corpus_now = _safe_float(profile.get("savings"))
    if target is None or target <= 0:
        out["fire_note"] = "run_fire"
    elif corpus_now is None or corpus_now < 0:
        out["fire_note"] = "missing_corpus"
    else:
        out["fire_pct"] = min(100.0, round(corpus_now / target * 100, 1))

    return out


def _weakest_dimensions(health: dict | None, n: int = 2) -> list[dict]:
    if not health:
        return []
    analysis = health.get("analysis") or {}
    radar = analysis.get("radar_chart") or []
    rows = [r for r in radar if isinstance(r, dict) and "score" in r]
    rows.sort(key=lambda r: int(r["score"]))
    return [{"label": r.get("axis", "—"), "score": int(r["score"])} for r in rows[:n]]


@sync_to_async
def _session_pop_first_report_banner(request) -> bool:
    if request.session.pop("show_first_report_banner", False):
        request.session.modified = True
        return True
    return False


@login_required
async def dashboard_view(request):
    """Dashboard — parallel backend calls, per-section errors, money-health cache (1h)."""
    uid = _fastapi_user_id(request)
    cache_key = f"money_health:{uid}"

    async def _profile():
        try:
            return await request.backend.get_profile(uid), None
        except Exception as e:
            logger.warning("dashboard get_profile: %s", e)
            return None, str(e)

    async def _portfolio():
        try:
            return await request.backend.get_portfolio_summary_optional(), None
        except Exception as e:
            logger.warning("dashboard portfolio: %s", e)
            return None, str(e)

    async def _nudges():
        try:
            return await request.backend.get_nudges(), None
        except Exception as e:
            logger.warning("dashboard nudges: %s", e)
            return [], str(e)

    async def _assumptions():
        try:
            return await request.backend.get_assumptions(), None
        except Exception as e:
            logger.warning("dashboard assumptions: %s", e)
            return None, str(e)

    async def _market():
        try:
            return await request.backend.market_pulse(), None
        except Exception as e:
            logger.warning("dashboard market_pulse: %s", e)
            return None, str(e)

    async def _radar():
        try:
            return await request.backend.opportunity_radar(), None
        except Exception as e:
            logger.warning("dashboard opportunity_radar: %s", e)
            return None, str(e)

    async def _money_health_fetch():
        hit = cache.get(cache_key)
        if hit is not None and _money_health_response_cacheable(hit):
            return hit, None, True
        if hit is not None:
            cache.delete(cache_key)
        try:
            data = await request.backend.money_health()
            if _money_health_response_cacheable(data):
                cache.set(cache_key, data, 3600)
            return data, None, False
        except Exception as e:
            logger.warning("dashboard money_health: %s", e)
            return None, str(e), False

    (
        (profile, profile_err),
        (portfolio, portfolio_err),
        (nudges, nudges_err),
        (assumptions, assumptions_err),
        (market_pulse, market_err),
        (radar, radar_err),
        (health, health_err, health_cached),
    ) = await asyncio.gather(
        _profile(),
        _portfolio(),
        _nudges(),
        _assumptions(),
        _market(),
        _radar(),
        _money_health_fetch(),
    )

    try:
        await request.backend.generate_nudges()
    except Exception:
        pass

    first_banner = await _session_pop_first_report_banner(request)
    metrics = _compute_dashboard_metrics(profile, portfolio)
    weak_dims = _weakest_dimensions(health)
    radar_analysis = (radar or {}).get("analysis") or {}
    signal_count = radar_analysis.get("signal_count")

    completeness = float((profile or {}).get("completeness_pct") or 0)
    missing_names = []
    if profile:
        raw = profile.get("missing_profile_fields") or []
        if isinstance(raw, list):
            missing_names = [str(x).replace("_", " ").title() for x in raw[:12]]

    ctx = {
        "profile": profile,
        "profile_error": profile_err,
        "portfolio": portfolio,
        "portfolio_error": portfolio_err,
        "nudges": nudges or [],
        "nudges_error": nudges_err,
        "assumptions": assumptions,
        "assumptions_error": assumptions_err,
        "health": health,
        "health_error": health_err,
        "health_cached": health_cached,
        "market_pulse": market_pulse,
        "market_error": market_err,
        "radar": radar,
        "radar_error": radar_err,
        "signal_count": signal_count,
        "dash_metrics": metrics,
        "weak_dimensions": weak_dims,
        "profile_warning_80": profile is not None and completeness < 80,
        "completeness_pct": completeness,
        "missing_field_labels": missing_names,
        "first_report_banner": first_banner,
    }
    return render(request, "dashboard/home.html", ctx)


@login_required
async def chat_view(request):
    """Chat interface — HTMX SSE streaming."""
    return render(request, "dashboard/chat.html")


@login_required
async def portfolio_view(request):
    """Portfolio overview + CAMS upload + X-Ray (when holdings exist)."""
    summary = None
    xray = None
    try:
        summary = await request.backend.get_portfolio_summary_optional()
    except Exception:
        summary = None
    if summary:
        try:
            xray = await request.backend.run_xray()
        except Exception:
            logger.exception("Portfolio X-Ray preload failed")
            xray = None
    return render(request, "dashboard/portfolio.html", {"portfolio": summary, "xray": xray})


@login_required
async def portfolio_upload(request):
    """Handle CAMS PDF upload (HTMX partial or JSON for onboarding wizard)."""
    if request.method != "POST":
        if "application/json" in (request.headers.get("Accept") or ""):
            return JsonResponse({"error": "Invalid method"}, status=405)
        return render(request, "dashboard/partials/upload_result.html", {"error": "Invalid method"})

    file = request.FILES.get("file")
    if not file:
        if "application/json" in (request.headers.get("Accept") or ""):
            return JsonResponse({"error": "No file selected"}, status=400)
        return render(request, "dashboard/partials/upload_result.html", {"error": "No file selected"})

    password = request.POST.get("password", "")
    try:
        result = await request.backend.upload_portfolio(file.read(), file.name, password)
        if "application/json" in (request.headers.get("Accept") or ""):
            return JsonResponse({"ok": True, **result})
        return render(request, "dashboard/partials/upload_result.html", {"result": result})
    except Exception as e:
        if "application/json" in (request.headers.get("Accept") or ""):
            return JsonResponse({"ok": False, "error": str(e)}, status=400)
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
    if result and result.get("analysis"):
        dims = result["analysis"].get("dimensions") or {}
        rows = []
        for key, val in dims.items():
            if isinstance(val, dict):
                rows.append((key, val, float(val.get("score") or 0)))
        rows.sort(key=lambda r: r[2])
        result["analysis"]["dimensions_sorted"] = [(k, v) for k, v, _ in rows]
    return render(request, "dashboard/partials/health_content.html", {"health": result})


@login_required
async def fire_view(request):
    """FIRE Planner page — profile + assumptions for sliders and chart."""
    profile = None
    assumptions = None
    try:
        profile = await request.backend.get_profile(_fastapi_user_id(request))
    except Exception:
        profile = None
    try:
        assumptions = await request.backend.get_assumptions()
    except Exception:
        assumptions = {}
    try:
        result = await request.backend.fire_planner()
    except Exception:
        result = None
    return render(
        request,
        "dashboard/fire.html",
        {"fire": result, "profile": profile or {}, "assumptions": assumptions or {}},
    )


@login_required
async def tax_view(request):
    """Tax Wizard page — merged with Tax Copilot (tabs)."""
    tax_result = None
    copilot_result = None
    profile = None
    active_tab = request.GET.get("tab", "regime")
    try:
        profile = await request.backend.get_profile(_fastapi_user_id(request))
    except Exception:
        profile = None
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
        "profile": profile if profile is not None else {},
    })


@login_required
async def budget_view(request):
    """Budget Coach page."""
    result = None
    expense_by_category: list[tuple[str, float]] = []
    try:
        result = await request.backend.budget_coach()
    except Exception:
        pass
    try:
        raw_exp = await request.backend.list_budget_expenses("", 300)
        by_cat: dict[str, float] = {}
        for row in raw_exp or []:
            cat = (row.get("category") or "other").strip().lower() or "other"
            by_cat[cat] = by_cat.get(cat, 0.0) + float(row.get("amount") or 0)
        expense_by_category = sorted(by_cat.items(), key=lambda x: -x[1])
    except Exception:
        expense_by_category = []
    return render(
        request,
        "dashboard/budget.html",
        {"budget": result, "expense_by_category": expense_by_category},
    )


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
    """Stress Test page — loads assumptions defaults for UI."""
    events = request.GET.getlist("events") or ["market_crash_30", "baby", "job_loss"]
    assumptions = None
    try:
        assumptions = await request.backend.get_assumptions()
    except Exception:
        assumptions = {}
    try:
        result = await request.backend.stress_test(events)
    except Exception:
        result = None
    return render(
        request,
        "dashboard/stress_test.html",
        {
            "stress": result,
            "events": events,
            "assumptions": assumptions or {},
        },
    )


@login_required
async def stress_test_run_api(request):
    """POST JSON { events, stress_scenario_params? } → agent JSON (Alpine stress UI)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    events = body.get("events") or ["market_crash_30"]
    if not isinstance(events, list):
        events = [str(events)]
    params = body.get("stress_scenario_params")
    if params is not None and not isinstance(params, dict):
        params = None
    try:
        out = await request.backend.stress_test(events, stress_scenario_params=params)
        return JsonResponse(out)
    except Exception as e:
        logger.exception("stress_test_run_api: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def settings_view(request):
    """User settings page."""
    settings_error = None
    settings_saved = False

    if request.method == "POST":
        section = (request.POST.get("form_section") or "profile").strip()
        data: dict = {}

        if section == "notifications":
            prefs = {
                "email_digest": request.POST.get("np_email_digest") == "on",
                "weekly_summary": request.POST.get("np_weekly_summary") == "on",
                "market_swings": request.POST.get("np_market_swings") == "on",
                "tax_deadlines": request.POST.get("np_tax_deadlines") == "on",
                "fire_milestones": request.POST.get("np_fire_milestones") == "on",
            }
            data["notification_prefs"] = json.dumps(prefs)
        elif section == "radar":
            for key in ("watchlist_stocks", "sector_interests", "alert_types"):
                val = request.POST.get(key)
                if val is not None:
                    data[key] = val
        else:
            int_keys = {
                "age", "fire_target_age", "goal_target_years", "dependents",
            }
            float_keys = {
                "monthly_income", "monthly_expenses", "monthly_fixed_expenses", "monthly_variable_expenses",
                "emergency_fund", "emergency_fund_amount", "monthly_emi", "hra", "rent_paid",
                "investments_80c", "section_80c_amount", "nps_contribution", "health_insurance_premium",
                "self_health_premium", "parents_health_premium", "epf_balance", "nps_balance", "ppf_balance",
                "basic_salary", "home_loan_interest", "home_loan_outstanding", "goal_target_amount",
                "term_insurance_cover", "life_insurance_cover", "health_insurance_cover", "annual_bonus",
                "monthly_sip_contribution",
                "partner_monthly_income", "partner_monthly_expenses", "partner_section_80c", "partner_nps_contribution",
                "lta_amount", "ytd_bonus_income", "fire_corpus_target",
            }
            str_keys = {
                "name", "city", "state", "language", "risk_appetite", "risk_tolerance", "employment_type",
                "primary_goal", "partner_name", "partner_tax_bracket", "whatsapp_phone",
                "watchlist_stocks", "sector_interests", "alert_types", "notification_prefs",
            }
            bool_keys = ("has_health_insurance", "has_nps", "parents_age_above_60", "has_home_loan", "is_metro")
            for key in int_keys | float_keys | str_keys:
                val = request.POST.get(key)
                if val is None or val == "":
                    continue
                if key in int_keys:
                    try:
                        data[key] = int(val)
                    except ValueError:
                        continue
                elif key in float_keys:
                    try:
                        data[key] = float(val)
                    except ValueError:
                        continue
                else:
                    data[key] = val
            for bk in bool_keys:
                if bk in request.POST:
                    data[bk] = request.POST.get(bk) in ("on", "true", "1", "yes")

        try:
            await request.backend.upsert_profile(data)
            _invalidate_money_health_cache(request)
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

    assumptions = None
    try:
        assumptions = await request.backend.get_assumptions()
    except Exception:
        pass

    nudges_hist = []
    try:
        nudges_hist = await request.backend.get_nudges()
    except Exception:
        pass

    notif_prefs: dict = {}
    raw_np = (profile or {}).get("notification_prefs")
    if raw_np:
        try:
            notif_prefs = json.loads(raw_np) if isinstance(raw_np, str) else dict(raw_np)
        except (json.JSONDecodeError, TypeError, ValueError):
            notif_prefs = {}

    return render(
        request,
        "dashboard/settings.html",
        {
            "profile": profile or {},
            "settings_error": settings_error,
            "settings_saved": settings_saved,
            "profile_load_error": profile_load_error,
            "assumptions": assumptions or {},
            "nudges_hist": nudges_hist,
            "notif_prefs": notif_prefs,
        },
    )


@login_required
async def assumptions_view(request):
    """Planning assumptions: HTML page, or JSON GET/POST to FastAPI /assumptions."""
    if request.method == "GET" and "application/json" in (request.headers.get("Accept") or ""):
        try:
            return JsonResponse(await request.backend.get_assumptions())
        except Exception as e:
            logger.exception("Assumptions JSON load: %s", e)
            return JsonResponse({"error": str(e)}, status=500)

    if request.method == "POST" and request.content_type and "application/json" in request.content_type:
        try:
            body = json.loads(request.body or b"{}")
            allowed = {
                "inflation_rate",
                "equity_lc_return",
                "equity_mc_return",
                "equity_sc_return",
                "debt_return",
                "sip_stepup_pct",
                "stress_scenarios",
            }
            payload = {k: v for k, v in body.items() if k in allowed}
            return JsonResponse(await request.backend.patch_assumptions(payload))
        except Exception as e:
            logger.exception("Assumptions save: %s", e)
            return JsonResponse({"error": str(e)}, status=500)

    return render(request, "settings/assumptions.html", {"error": None, "saved": False})


@login_required
async def onboarding_view(request):
    """Legacy /onboarding/ — forward to 3-step wizard."""
    return redirect("onboarding_wizard")


@login_required
async def notifications_view(request):
    """All notifications / nudges."""
    try:
        nudges = await request.backend.get_nudges()
    except Exception:
        nudges = []
    return render(request, "dashboard/notifications.html", {"nudges": nudges})


@login_required
async def export_reports_view(request):
    """Hub for CSV/PDF exports (proxies to FastAPI)."""
    return render(request, "dashboard/export.html")


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
    profile_ctx = None
    try:
        profile_ctx = await request.backend.get_profile(_fastapi_user_id(request))
    except Exception:
        profile_ctx = {}
    return render(request, "dashboard/couples.html", {
        "couples": result,
        "partner": partner,
        "link_message": link_message,
        "profile": profile_ctx or {},
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
        suffix = ""
        try:
            psum = await request.backend.get_portfolio_summary_optional()
            if psum and isinstance(psum, dict):
                funds = psum.get("funds") or []
                names = [str(f.get("fund_name") or "") for f in funds[:12] if f.get("fund_name")]
                if names:
                    suffix = (
                        "\n\n[Portfolio context: user holds mutual funds including "
                        + ", ".join(names)
                        + ". Tailor macro/regulatory answers to these exposures where relevant.]"
                    )
        except Exception:
            pass
        try:
            result = await request.backend.et_research(query + suffix)
        except Exception:
            pass
    return render(request, "dashboard/research.html", {"research": result, "query": query})


@login_required
async def opportunity_radar_view(request):
    """PS6 — Opportunity Radar (signals, watchlist-aware)."""
    radar = None
    try:
        radar = await request.backend.opportunity_radar()
    except Exception as e:
        logger.error("Opportunity radar view: %s", e)
    return render(request, "dashboard/opportunity_radar.html", {"radar": radar})


@login_required
async def chart_intelligence_view(request):
    """PS6 — Chart pattern scan for one symbol (NSE)."""
    symbol = (request.GET.get("symbol") or "").strip().upper()
    tf = (request.GET.get("tf") or "3mo").strip()
    chart = None
    try:
        chart = await request.backend.chart_pattern(symbol or None, tf or "3mo")
    except Exception as e:
        logger.error("Chart intelligence view: %s", e)
    return render(
        request,
        "dashboard/chart_intelligence.html",
        {"chart": chart, "symbol": symbol, "tf": tf},
    )


@login_required
async def voice_view(request):
    """Voice Agent interface."""
    return render(request, "dashboard/voice.html")


@login_required
async def expense_analytics_view(request):
    """Expense Analytics — log expenses, list recent rows, charts from aggregated data."""
    if request.method == "POST":
        action = (request.POST.get("action") or "add").strip()
        if action == "delete":
            eid = (request.POST.get("expense_id") or "").strip()
            if eid:
                try:
                    await request.backend.delete_budget_expense(eid)
                    request.session["expense_flash"] = {
                        "kind": "ok",
                        "text": "Expense removed.",
                    }
                except Exception as e:
                    logger.exception("Delete expense: %s", e)
                    request.session["expense_flash"] = {
                        "kind": "err",
                        "text": "Could not remove that expense. Check the API is running.",
                    }
        else:
            category = (request.POST.get("category") or "").strip()
            try:
                amount = float(request.POST.get("amount") or 0)
            except ValueError:
                amount = 0.0
            desc = (request.POST.get("description") or "").strip()
            exp_date = (request.POST.get("expense_date") or "").strip()
            pay = (request.POST.get("payment_method") or "upi").strip() or "upi"
            recurring = request.POST.get("is_recurring") == "on"
            if not category or amount <= 0:
                request.session["expense_flash"] = {
                    "kind": "err",
                    "text": "Choose a category and enter an amount greater than zero.",
                }
            else:
                try:
                    await request.backend.post_budget_expense(
                        category=category[:100],
                        amount=amount,
                        description=desc[:500],
                        expense_date=exp_date,
                        payment_method=pay[:50],
                        is_recurring=recurring,
                    )
                    request.session["expense_flash"] = {
                        "kind": "ok",
                        "text": "Expense saved. Charts update from your logged entries.",
                    }
                except Exception as e:
                    logger.exception("Log expense: %s", e)
                    request.session["expense_flash"] = {
                        "kind": "err",
                        "text": "Could not save expense. Ensure the FastAPI backend is running.",
                    }
        return redirect("expense_analytics")

    expense_flash = request.session.pop("expense_flash", None)
    recent_expenses: list = []
    try:
        recent_expenses = await request.backend.list_budget_expenses("", 100)
    except Exception:
        pass
    result = None
    try:
        result = await request.backend.expense_analytics()
    except Exception as e:
        logger.error("Expense analytics error: %s", e)
    return render(
        request,
        "dashboard/expense_analytics.html",
        {
            "expense": result,
            "recent_expenses": recent_expenses,
            "expense_flash": expense_flash,
            "today_iso": date.today().isoformat(),
        },
    )


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
    profile = None
    try:
        profile = await request.backend.get_profile(_fastapi_user_id(request))
    except Exception:
        profile = {}
    if request.method == "POST":
        message = request.POST.get("message", "")
        if message:
            try:
                result = await request.backend.life_event_advisor(message)
            except Exception as e:
                logger.error("Life event advisor error: %s", e)
    return render(
        request,
        "dashboard/life_events.html",
        {"result": result, "message": message, "profile": profile or {}},
    )


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
async def api_nudges_pending(request):
    """GET pending nudges as JSON (sidebar panel)."""
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    try:
        nudges = await request.backend.get_nudges()
        return JsonResponse(nudges, safe=False)
    except Exception as e:
        logger.exception("api_nudges_pending: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_profile_patch(request):
    """PATCH partial profile (e.g. chat field_request)."""
    if request.method != "PATCH":
        return JsonResponse({"error": "PATCH required"}, status=405)
    try:
        data = json.loads(request.body or b"{}")
        result = await request.backend.patch_profile(data)
        _invalidate_money_health_cache(request)
        return JsonResponse(result)
    except Exception as e:
        logger.exception("api_profile_patch: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
async def api_profile_upsert(request):
    """Proxy POST to FastAPI /profile/upsert — used by onboarding form."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        result = await request.backend.upsert_profile(data)
        _invalidate_money_health_cache(request)
        return JsonResponse(result)
    except Exception as e:
        logger.exception("Profile upsert proxy error: %s", e)
        hint = (
            " Ensure the FastAPI backend is running (e.g. make backend) and Postgres is up; "
            "avoid `docker compose down -v` if you want to keep saved profiles."
        )
        return JsonResponse({"error": str(e) + hint}, status=500)


@login_required
async def api_chat_history(request):
    """Proxy GET /chat/history for dashboard snippet."""
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    try:
        lim = int(request.GET.get("limit", "20"))
    except ValueError:
        lim = 20
    try:
        rows = await request.backend.get_chat_history(max(1, min(lim, 50)))
        return JsonResponse(rows, safe=False)
    except Exception as e:
        logger.exception("chat history: %s", e)
        return JsonResponse([], safe=False)


@login_required
async def api_agent_money_health(request):
    """Proxy POST /agents/money-health (e.g. after onboarding)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = await request.backend.money_health()
        if _money_health_response_cacheable(data):
            cache.set(f"money_health:{_fastapi_user_id(request)}", data, 3600)
        return JsonResponse({"ok": True, **data})
    except Exception as e:
        logger.exception("money-health proxy: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


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
    profile, health, portfolio, tax, fire, stress = None, None, None, None, None, None
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
    try:
        fire = await request.backend.fire_planner()
    except Exception:
        pass
    try:
        stress = await request.backend.stress_test(["market_crash_30"])
    except Exception:
        pass
    return render(request, "dashboard/report_card.html", {
        "profile": profile,
        "health": health,
        "portfolio": portfolio,
        "tax": tax,
        "fire": fire,
        "stress": stress,
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
