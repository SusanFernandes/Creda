#!/usr/bin/env python3
"""
Creda Finance API — Comprehensive Test Suite
Tests all v2 finance endpoints via the Gateway (port 8080).
Run: python tests/test_finance_api.py
"""
import requests
import json
import time
from typing import Any

GATEWAY = "http://localhost:8080"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def post(path: str, payload: dict, timeout: int = 30) -> dict:
    """POST to gateway and return JSON."""
    url = f"{GATEWAY}{path}"
    start = time.time()
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        elapsed = round((time.time() - start) * 1000)
        r.raise_for_status()
        return {"ok": True, "status": r.status_code, "data": r.json(), "ms": elapsed}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Connection refused — is the gateway running on :8080?"}
    except requests.exceptions.HTTPError as e:
        return {"ok": False, "status": r.status_code, "error": str(e), "body": r.text[:300]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get(path: str, timeout: int = 10) -> dict:
    url = f"{GATEWAY}{path}"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return {"ok": True, "status": r.status_code, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def print_result(label: str, result: dict) -> bool:
    ok = result.get("ok", False)
    icon = "✅" if ok else "❌"
    ms  = f"  [{result['ms']}ms]" if "ms" in result else ""
    print(f"{icon} {label}{ms}")
    if not ok:
        print(f"   ERROR: {result.get('error') or result.get('body', 'unknown')}")
    return ok

# ─── Test Sections ────────────────────────────────────────────────────────────

passed = failed = 0

def run(label: str, result: dict) -> None:
    global passed, failed
    ok = print_result(label, result)
    if ok: passed += 1
    else:  failed += 1

# ── 0. Health ──────────────────────────────────────────────────────────────────
print("\n═══ 0. Gateway Health ════════════════════════════════")
run("GET /health", get("/health"))

# ── 1. Profile ────────────────────────────────────────────────────────────────
print("\n═══ 1. User Profile ══════════════════════════════════")

profile_payload = {
    "user_id": "test_user_001",
    "name": "Priya Sharma",
    "age": 29,
    "income": 80000,
    "expenses": 45000,
    "savings": 200000,
    "dependents": 0,
    "risk_tolerance": 7,
    "goal_type": "wealth_creation",
    "time_horizon": 10,
    "language": "english",
    "monthly_emi": 0,
    "emergency_fund": 150000,
    "has_health_insurance": True,
    "investments_80c": 100000,
    "nps_contribution": 50000,
}

run("POST /profile/upsert",         post("/profile/upsert", profile_payload))
run("GET  /profile/{user_id}",       get("/profile/test_user_001"))

# ── 2. Chat / LangGraph ───────────────────────────────────────────────────────
print("\n═══ 2. Chat (LangGraph) ══════════════════════════════")

chat_cases = [
    ("General greeting",      {"message": "Hello, what can you help me with?", "user_id": "test_user_001", "session_id": "sess_001"}),
    ("SIP enquiry",           {"message": "I want to start a SIP of 10000 rupees monthly. What returns can I expect in 10 years?", "user_id": "test_user_001", "session_id": "sess_001"}),
    ("Budget advice",         {"message": "I spend 45000 a month but earn 80000. How can I save more?", "user_id": "test_user_001", "session_id": "sess_001"}),
    ("FIRE planning",         {"message": "I want to retire at 45. Is it possible?", "user_id": "test_user_001", "session_id": "sess_001"}),
    ("Tax planning",          {"message": "What are the best tax saving options for my income?", "user_id": "test_user_001", "session_id": "sess_001"}),
    ("Portfolio advice",      {"message": "I have 200000 to invest. Suggest portfolio allocation.", "user_id": "test_user_001", "session_id": "sess_001"}),
    ("Navigation intent",     {"message": "Show me my dashboard", "user_id": "test_user_001", "session_id": "sess_001"}),
    ("Hindi query",           {"message": "Mujhe apna portfolio dekhna hai", "user_id": "test_user_001", "session_id": "sess_001", "language": "hindi"}),
]

for label, payload in chat_cases:
    result = post("/chat", payload)
    run(f"Chat — {label}", result)
    if result.get("ok"):
        data = result["data"]
        resp = data.get("data", {}).get("response") or data.get("response", "")
        intent = data.get("data", {}).get("intent") or data.get("intent", "")
        print(f"   intent={intent!r}  response_preview={resp[:80]!r}")

# ── 3. Money Health Score ──────────────────────────────────────────────────────
print("\n═══ 3. Money Health Score ════════════════════════════")

health_cases = [
    ("Good profile — salaried",  {**profile_payload, "life_insurance_cover": 5000000}),
    ("Poor profile — no savings", {"user_id": "test_poor", "income": 30000, "expenses": 29000, "emergency_fund": 0, "has_health_insurance": False}),
    ("High earner",              {"user_id": "test_rich", "income": 300000, "expenses": 80000, "savings": 5000000, "investments_80c": 150000}),
]

for label, payload in health_cases:
    run(f"POST /money-health-score — {label}", post("/money-health-score", payload))

# ── 4. SIP Calculator ─────────────────────────────────────────────────────────
print("\n═══ 4. SIP Calculator ════════════════════════════════")

sip_cases = [
    ("10k/mo, 12%, 15yr",       {"monthly_amount": 10000, "expected_return": 12, "years": 15}),
    ("5k/mo, 8%, 20yr",         {"monthly_amount": 5000,  "expected_return": 8,  "years": 20}),
    ("25k/mo, 15%, 10yr, +10%", {"monthly_amount": 25000, "expected_return": 15, "years": 10, "step_up_percent": 10}),
    ("1L/mo, 12%, 30yr",        {"monthly_amount": 100000,"expected_return": 12, "years": 30}),
    ("Minimal — 500/mo, 7%, 1yr",{"monthly_amount": 500,  "expected_return": 7,  "years": 1}),
]

for label, payload in sip_cases:
    result = post("/sip-calculator", payload)
    run(f"SIP — {label}", result)
    if result.get("ok"):
        d = result["data"].get("data", result["data"])
        print(f"   invested={d.get('total_invested')}  value={d.get('expected_value')}  gain={d.get('wealth_gain')}")

# ── 5. FIRE Planner ───────────────────────────────────────────────────────────
print("\n═══ 5. FIRE Planner ══════════════════════════════════")

fire_cases = [
    ("Standard early retirement",   {"user_id": "test_user_001", "monthly_expenses": 50000, "current_savings": 500000,  "monthly_investment": 25000, "expected_return": 12, "inflation_rate": 6}),
    ("Aggressive investor",         {"user_id": "test_user_001", "monthly_expenses": 80000, "current_savings": 2000000, "monthly_investment": 80000, "expected_return": 15, "inflation_rate": 5}),
    ("Low income saver",            {"user_id": "test_low",      "monthly_expenses": 20000, "current_savings": 50000,   "monthly_investment": 5000,  "expected_return": 10, "inflation_rate": 6}),
]

for label, payload in fire_cases:
    result = post("/fire-planner", payload)
    run(f"FIRE — {label}", result)
    if result.get("ok"):
        d = result["data"].get("data", result["data"])
        print(f"   fire_number={d.get('fire_number')}  years_to_fire={d.get('years_to_fire')}  gap={d.get('current_gap')}")

# ── 6. Tax Wizard ─────────────────────────────────────────────────────────────
print("\n═══ 6. Tax Wizard ════════════════════════════════════")

tax_cases = [
    ("12L income, max deductions",   {"user_id": "test_user_001", "annual_income": 1200000, "investments_80c": 150000, "nps_contribution": 50000, "health_insurance_premium": 25000}),
    ("5L income, no deductions",     {"user_id": "test_user_002", "annual_income": 500000}),
    ("30L income, home loan HRA",    {"user_id": "test_user_003", "annual_income": 3000000, "investments_80c": 150000, "home_loan_interest": 200000, "hra": 300000}),
    ("7L salaried, standard deduction", {"user_id": "test_user_004", "annual_income": 700000, "investments_80c": 100000}),
]

for label, payload in tax_cases:
    result = post("/tax-wizard", payload)
    run(f"Tax — {label}", result)
    if result.get("ok"):
        d = result["data"].get("data", result["data"])
        print(f"   old={d.get('old_regime_tax')}  new={d.get('new_regime_tax')}  recommended={d.get('recommended')}  savings={d.get('savings')}")

# ── 7. Portfolio Stress Test ───────────────────────────────────────────────────
print("\n═══ 7. Portfolio Stress Test ═════════════════════════")

stress_cases = [
    ("Market crash",       {"user_id": "test_user_001", "event_type": "market_crash",       "severity": 0.3}),
    ("Job loss",           {"user_id": "test_user_001", "event_type": "job_loss",            "severity": 1.0}),
    ("Medical emergency",  {"user_id": "test_user_001", "event_type": "medical_emergency",   "severity": 0.5}),
    ("Home purchase",      {"user_id": "test_user_001", "event_type": "home_purchase"}),
    ("New baby",           {"user_id": "test_user_001", "event_type": "baby"}),
    ("Marriage",           {"user_id": "test_user_001", "event_type": "marriage"}),
]

for label, payload in stress_cases:
    run(f"Stress — {label}", post("/portfolio/stress-test", payload))

# ── 8. Couples Planner ────────────────────────────────────────────────────────
print("\n═══ 8. Couples Planner ═══════════════════════════════")

couples_cases = [
    ("Basic",        {"partner1_user_id": "test_user_001", "partner2_user_id": "test_user_002", "combined_goal": "Buy home in 5 years"}),
    ("Retirement",   {"partner1_user_id": "test_user_001", "partner2_user_id": "test_user_002", "combined_goal": "Retire at 55 with 3 Cr corpus"}),
]

for label, payload in couples_cases:
    run(f"Couples — {label}", post("/couples-planner", payload))

# ── 9. RAG Knowledge Query ────────────────────────────────────────────────────
print("\n═══ 9. RAG Knowledge Query ═══════════════════════════")

rag_queries = [
    "What is the difference between ELSS and PPF?",
    "How does SIP rupee cost averaging work?",
    "What are the tax slabs for FY 2024-25 under the new regime?",
    "Explain term insurance vs ULIP for a 30-year-old",
    "What is the 50-30-20 budgeting rule?",
]

for query in rag_queries:
    result = post("/rag_query", {"query": query, "user_id": "test_user_001"})
    run(f"RAG — {query[:50]}", result)
    if result.get("ok"):
        d = result["data"].get("data", result["data"])
        ans = d.get("answer") or d.get("response", "")
        print(f"   answer_preview={ans[:80]!r}")

# ── Summary ───────────────────────────────────────────────────────────────────
total = passed + failed
print(f"\n{'═' * 55}")
print(f"Finance API Tests: {passed}/{total} passed  ({failed} failed)")
print(f"{'═' * 55}")
if failed:
    print("⚠️  Some tests failed — check that backend services are running:")
    print("   Gateway      → http://localhost:8080")
    print("   Finance Svc  → http://localhost:8001")
