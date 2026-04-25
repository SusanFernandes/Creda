#!/usr/bin/env python3
"""
CREDA End-to-End Demo Test
============================
Tests all 11 scenes from the hackathon demo scenario end-to-end.
Requires: FastAPI backend on port 8001, seeded with demo data.

API paths used: ``GET /profile/{user_id}`` (not ``/profile``), ``GET /nudges/pending``.

Usage:
    python test_e2e_demo.py               # full run
    python test_e2e_demo.py --scene 2     # run single scene
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Any

import httpx

BACKEND = "http://localhost:8001"
ARJUN = {"x-user-id": "100", "x-user-email": "arjun@demo.creda.in"}
PRIYA = {"x-user-id": "101", "x-user-email": "priya@demo.creda.in"}


@dataclass
class Result:
    scene: int
    name: str
    passed: bool
    detail: str = ""
    data: Any = None


results: list[Result] = []


def _check(condition: bool, msg: str) -> None:
    if not condition:
        raise AssertionError(msg)


async def scene_1(client: httpx.AsyncClient):
    """Scene 1 — Dashboard: Money Health Score + Nudges"""
    # Get profile
    r = await client.get(f"{BACKEND}/profile/100", headers=ARJUN)
    _check(r.status_code == 200, f"Profile GET failed: {r.status_code}")
    profile = r.json()
    _check(profile.get("full_name") == "Arjun Mehta", f"Wrong name: {profile.get('full_name')}")

    # Generate nudges
    r = await client.post(f"{BACKEND}/nudges/generate", headers=ARJUN)
    _check(r.status_code == 200, f"Nudge generate failed: {r.status_code}")

    # Fetch nudges
    r = await client.get(f"{BACKEND}/nudges/pending", headers=ARJUN)
    _check(r.status_code == 200, f"Nudges GET failed: {r.status_code}")
    nudges = r.json()
    _check(len(nudges) > 0, "No nudges returned")

    # Money Health
    r = await client.post(f"{BACKEND}/agents/money-health", json={"language": "en"}, headers=ARJUN)
    _check(r.status_code == 200, f"Money health failed: {r.status_code}")
    health = r.json()
    analysis = health.get("analysis", {})
    _check("overall_score" in analysis, "Missing overall_score")
    _check("grade" in analysis, "Missing grade")
    _check("dimensions" in analysis, "Missing dimensions")

    return Result(1, "Dashboard + Health Score", True,
                  f"Score={analysis['overall_score']}, Grade={analysis['grade']}, Nudges={len(nudges)}",
                  {"score": analysis["overall_score"], "grade": analysis["grade"]})


async def scene_2(client: httpx.AsyncClient):
    """Scene 2 — Portfolio X-Ray: Overlap + Benchmark"""
    # Portfolio summary
    r = await client.get(f"{BACKEND}/portfolio/summary", headers=ARJUN)
    _check(r.status_code == 200, f"Portfolio summary failed: {r.status_code}")
    summary = r.json()
    _check(summary.get("funds_count", 0) > 0, "No funds in portfolio")

    # X-Ray analysis
    r = await client.post(f"{BACKEND}/portfolio/xray", headers=ARJUN)
    _check(r.status_code == 200, f"X-Ray failed: {r.status_code}")
    xray = r.json()
    _check("overlap_categories" in xray, "Missing overlap_categories")
    _check("top_performers" in xray, "Missing top_performers")
    _check("bottom_performers" in xray, "Missing bottom_performers")
    _check("recommendations" in xray, "Missing recommendations")

    return Result(2, "Portfolio X-Ray", True,
                  f"Funds={summary['funds_count']}, Overlap={len(xray['overlap_categories'])} cats, Alpha={xray.get('alpha_vs_nifty', 'N/A')}",
                  {"overlap": xray["overlap_categories"]})


async def scene_3(client: httpx.AsyncClient):
    """Scene 3 — Tax Wizard: Regime + Missed Deductions"""
    r = await client.post(f"{BACKEND}/agents/tax-wizard", json={"language": "en"}, headers=ARJUN)
    _check(r.status_code == 200, f"Tax wizard failed: {r.status_code}")
    tax = r.json()
    analysis = tax.get("analysis", {})
    _check("old_regime" in analysis, "Missing old_regime")
    _check("new_regime" in analysis, "Missing new_regime")
    _check("better_regime" in analysis, "Missing better_regime")
    _check("missed_deductions" in analysis, "Missing missed_deductions")

    return Result(3, "Tax Wizard", True,
                  f"Better={analysis['better_regime']}, Savings=₹{analysis.get('savings', 0):,.0f}, Missed={len(analysis.get('missed_deductions', []))}",
                  {"regime": analysis["better_regime"]})


async def scene_4(client: httpx.AsyncClient):
    """Scene 4 — Life Event: ₹3L Bonus Allocation"""
    r = await client.post(f"{BACKEND}/agents/life-event-advisor",
                          json={"message": "I received a ₹3 lakh bonus", "language": "en"},
                          headers=ARJUN)
    _check(r.status_code == 200, f"Life event failed: {r.status_code}")
    result = r.json()
    analysis = result.get("analysis", {})
    _check("allocations" in analysis, "Missing allocations")
    allocs = analysis["allocations"]
    _check(len(allocs) > 0, "No allocations returned")

    return Result(4, "Life Event — Bonus", True,
                  f"Allocations={len(allocs)}, Score change: {analysis.get('current_health_score', '?')}→{analysis.get('projected_health_score', '?')}",
                  {"allocations": allocs})


async def scene_5(client: httpx.AsyncClient):
    """Scene 5 — Couples Finance: Joint Analysis with Priya"""
    r = await client.post(f"{BACKEND}/agents/couples-finance",
                          json={"partner_income": 0, "partner_expenses": 0, "language": "en"},
                          headers=ARJUN)
    _check(r.status_code == 200, f"Couples finance failed: {r.status_code}")
    result = r.json()
    analysis = result.get("analysis", {})
    _check("combined_income" in analysis, "Missing combined_income")
    _check("recommended_split" in analysis or "recommended" in analysis, "Missing split recommendation")

    return Result(5, "Couples Finance", True,
                  f"Combined=₹{analysis.get('combined_income', 0):,.0f}, Split={analysis.get('recommended', analysis.get('recommended_split', 'N/A'))}",
                  {"combined": analysis.get("combined_income")})


async def scene_6(client: httpx.AsyncClient):
    """Scene 6 — FIRE Planner: Roadmap + Glide Path"""
    r = await client.post(f"{BACKEND}/agents/fire-planner", json={"language": "en"}, headers=ARJUN)
    _check(r.status_code == 200, f"FIRE planner failed: {r.status_code}")
    result = r.json()
    analysis = result.get("analysis", {})
    _check("fire_number" in analysis, "Missing fire_number")
    _check("required_sip" in analysis, "Missing required_sip")
    _check("roadmap" in analysis, "Missing roadmap")
    _check(len(analysis.get("roadmap", [])) > 0, "Empty roadmap")
    _check("glide_path" in analysis, "Missing glide_path")

    return Result(6, "FIRE Planner", True,
                  f"FIRE=₹{analysis['fire_number']:,.0f}, SIP=₹{analysis['required_sip']:,.0f}/mo, Roadmap={len(analysis['roadmap'])} years",
                  {"fire_number": analysis["fire_number"]})


async def scene_7(client: httpx.AsyncClient):
    """Scene 7 — AI Chat Agent"""
    r = await client.post(f"{BACKEND}/chat",
                          json={"message": "What is my current portfolio value?", "language": "en"},
                          headers=ARJUN)
    _check(r.status_code == 200, f"Chat failed: {r.status_code}")
    result = r.json()
    _check("response" in result or "message" in result, "No response from chat")
    response_text = result.get("response", result.get("message", ""))
    _check(len(response_text) > 10, f"Chat response too short: {response_text[:50]}")

    return Result(7, "AI Chat", True, f"Response length: {len(response_text)} chars")


async def scene_8(client: httpx.AsyncClient):
    """Scene 8 — Market Pulse: Live Indices + Impact"""
    r = await client.post(f"{BACKEND}/agents/market-pulse", json={"language": "en"}, headers=ARJUN)
    _check(r.status_code == 200, f"Market pulse failed: {r.status_code}")
    result = r.json()
    analysis = result.get("analysis", {})
    _check("indices" in analysis or "headlines" in analysis, "Missing market data")

    return Result(8, "Market Pulse", True,
                  f"Keys: {list(analysis.keys())[:5]}")


async def scene_9(client: httpx.AsyncClient):
    """Scene 9 — WhatsApp: Verify endpoint exists"""
    # Just verify the endpoint responds (actual WhatsApp requires Twilio)
    r = await client.get(f"{BACKEND}/whatsapp/webhook")
    # Should return 200 or 405 (method not allowed for GET)
    _check(r.status_code in (200, 405, 422), f"WhatsApp webhook not available: {r.status_code}")

    return Result(9, "WhatsApp Endpoint", True, f"Status: {r.status_code}")


async def scene_10(client: httpx.AsyncClient):
    """Scene 10 — SEBI Compliance: Audit Trail"""
    r = await client.get(f"{BACKEND}/compliance/audit-trail?limit=5", headers=ARJUN)
    _check(r.status_code == 200, f"Compliance failed: {r.status_code}")
    result = r.json()
    _check(isinstance(result, (list, dict)), "Invalid compliance response")

    return Result(10, "SEBI Compliance", True, f"Response type: {type(result).__name__}")


async def scene_11(client: httpx.AsyncClient):
    """Scene 11 — Multilingual: Hindi Mode"""
    r = await client.post(f"{BACKEND}/agents/money-health",
                          json={"language": "hi"},
                          headers=ARJUN)
    _check(r.status_code == 200, f"Hindi health failed: {r.status_code}")
    result = r.json()
    _check("response" in result or "analysis" in result, "No Hindi response")

    return Result(11, "Multilingual (Hindi)", True, f"Response keys: {list(result.keys())}")


SCENES = {
    1: scene_1, 2: scene_2, 3: scene_3, 4: scene_4, 5: scene_5,
    6: scene_6, 7: scene_7, 8: scene_8, 9: scene_9, 10: scene_10, 11: scene_11,
}


async def main(scenes_to_run: list[int] | None = None):
    print()
    print("=" * 65)
    print("  CREDA E2E Demo Test — Arjun's 8-Minute Story")
    print("=" * 65)
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Health check
        try:
            r = await client.get(f"{BACKEND}/health")
            if r.status_code != 200:
                print(f"  ✗ Backend not healthy: {r.status_code}")
                return
        except httpx.ConnectError:
            print(f"  ✗ Cannot connect to {BACKEND}")
            print("    Start the backend: cd backend && uvicorn app.main:app --port 8001")
            return

        targets = scenes_to_run or list(range(1, 12))
        passed = 0
        failed = 0

        for scene_num in targets:
            fn = SCENES.get(scene_num)
            if not fn:
                print(f"  ? Scene {scene_num} not found")
                continue
            try:
                result = await fn(client)
                results.append(result)
                passed += 1
                print(f"  ✓ Scene {result.scene:2d} — {result.name}")
                if result.detail:
                    print(f"            {result.detail}")
            except AssertionError as e:
                results.append(Result(scene_num, fn.__doc__.split("—")[1].strip() if "—" in fn.__doc__ else fn.__doc__, False, str(e)))
                failed += 1
                print(f"  ✗ Scene {scene_num:2d} — FAILED: {e}")
            except Exception as e:
                results.append(Result(scene_num, f"Scene {scene_num}", False, f"Error: {e}"))
                failed += 1
                print(f"  ✗ Scene {scene_num:2d} — ERROR: {type(e).__name__}: {e}")

        print()
        print("-" * 65)
        print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
        print("-" * 65)

        if failed == 0:
            print("  🎯 ALL SCENES PASSED — Demo is ready!")
        else:
            print(f"  ⚠  {failed} scene(s) need attention")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CREDA E2E Demo Test")
    parser.add_argument("--scene", type=int, help="Run specific scene number (1-11)")
    args = parser.parse_args()

    scenes = [args.scene] if args.scene else None
    asyncio.run(main(scenes))
