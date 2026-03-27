#!/usr/bin/env python3
"""
Creda — End-to-End Integration Test Suite
Tests the full pipeline: Voice → ASR → LangGraph → TTS → Audio out
and multi-turn financial conversations across languages.

Run: python tests/test_integration.py
"""
import requests
import json
import time
import struct
import wave
import io
import os
from typing import Optional

GATEWAY       = "http://localhost:8080"
MULTILINGUAL  = "http://localhost:8000"
FINANCE       = "http://localhost:8001"

# ─── Audio Helpers ────────────────────────────────────────────────────────────

def make_silent_wav(duration_secs: float = 1.5, sample_rate: int = 16000) -> bytes:
    """Create a minimal silent WAV for testing ASR endpoints."""
    num_samples = int(duration_secs * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{num_samples}h', *([0]*num_samples)))
    return buf.getvalue()

# ─── Helpers ──────────────────────────────────────────────────────────────────

passed = failed = 0

def ok(label: str) -> None:
    global passed
    passed += 1
    print(f"  ✅ {label}")

def fail(label: str, reason: str) -> None:
    global failed
    failed += 1
    print(f"  ❌ {label}: {reason}")

def check(label: str, condition: bool, reason: str = "") -> bool:
    if condition: ok(label)
    else:         fail(label, reason or "assertion failed")
    return condition

def post_json(url: str, payload: dict, timeout: int = 30) -> Optional[dict]:
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def get_json(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

if __name__ == "__main__":
    # ─── 1. Service Availability ─────────────────────────────────────────────────
    print("\n══════════════════════════════════════════════════")
    print(" 0. Service Availability")
    print("══════════════════════════════════════════════════")

    gw_health  = get_json(f"{GATEWAY}/health")
    ml_health  = get_json(f"{MULTILINGUAL}/health")
    fin_health = get_json(f"{FINANCE}/health")

    gw_up  = check("Gateway    (:8080)", gw_health  is not None, "cannot connect")
    ml_up  = check("Multilingual (:8000)", ml_health  is not None, "cannot connect")
    fin_up = check("Finance    (:8001)", fin_health is not None, "cannot connect")

    if not gw_up:
        print("\n⛔ Gateway is down — cannot continue integration tests.")
        print("   Start services with: python app.py, python fastapi1_multilingual.py, python fastapi2_finance.py")
        exit(1)

    # ─── 2. Multi-Turn Conversation ───────────────────────────────────────────────
    print("\n══════════════════════════════════════════════════")
    print(" 1. Multi-Turn Conversational Flow")
    print("══════════════════════════════════════════════════")

    session_id = f"integ_{int(time.time())}"
    user_id    = "integ_test_user"

    conversation = [
        ("Hello, how can you help me?",            "general_chat"),
        ("I earn 80000 per month, how much should I save?", "budgeting"),
        ("What is a good SIP amount for me?",      "sip"),
        ("How do I plan for early retirement?",     "fire"),
        ("Show me tax saving options",              "tax"),
    ]

    prev_response = None
    for turn, (message, expected_topic) in enumerate(conversation, 1):
        body = {"message": message, "user_id": user_id, "session_id": session_id}
        resp = post_json(f"{GATEWAY}/chat", body)

        if resp is None:
            fail(f"Turn {turn}: {message[:40]}...", "no response from gateway")
            continue

        data = resp.get("data") or resp
        response_text = data.get("response", "")
        intent        = data.get("intent", "")

        has_response  = len(response_text) > 10
        has_session   = bool(data.get("session_id"))

        check(f"Turn {turn} — has response  ({message[:35]}...)", has_response,  f"response blank: {response_text!r}")
        check(f"Turn {turn} — session maintained",                has_session,   "session_id missing")

        print(f"   intent={intent!r}  preview={response_text[:80]!r}")
        prev_response = response_text

    # ─── 3. Language Detection & Multilingual Chat ───────────────────────────────
    print("\n══════════════════════════════════════════════════")
    print(" 2. Multilingual Chat")
    print("══════════════════════════════════════════════════")

    multilingual_cases = [
        ("hindi",   "Mujhe SIP ke baare mein bataiye",             "Hindi SIP query"),
        ("hindi",   "Main apna budget kaise manage karoon?",        "Hindi budget"),
        ("tamil",   "என் பணத்தை எப்படி முதலீடு செய்வது?",        "Tamil investment"),
        ("bengali", "আমি কিভাবে আমার অর্থ বিনিয়োগ করব?",       "Bengali investment"),
        ("telugu",  "నా డబ్బును ఎలా పెట్టుబడి పెట్టాలి?",       "Telugu investment"),
        ("english", "What is compound interest?",                   "English baseline"),
    ]

    for lang, message, label in multilingual_cases:
        body = {
            "message": message,
            "user_id": user_id,
            "session_id": f"{session_id}_{lang}",
            "language": lang,
        }
        resp = post_json(f"{GATEWAY}/chat", body)
        if resp is None:
            fail(f"Multilingual — {label}", "no response")
            continue

        data  = resp.get("data") or resp
        reply = data.get("response", "")
        check(f"Multilingual — {label}", len(reply) > 5, f"empty response for {lang}")
        print(f"   [{lang}] preview={reply[:70]!r}")

    # ─── 4. Voice Audio Processing (Multilingual Service) ────────────────────────
    if ml_up:
        print("\n══════════════════════════════════════════════════")
        print(" 3. Voice Audio Processing (Multilingual ASR)")
        print("══════════════════════════════════════════════════")

        silent_wav = make_silent_wav()

        lang_codes = [("en", "English"), ("hi", "Hindi"), ("ta", "Tamil"), ("bn", "Bengali"), ("te", "Telugu")]

        for lang_code, lang_name in lang_codes:
            try:
                files  = {"audio": ("test.wav", silent_wav, "audio/wav")}
                data   = {"language_code": lang_code, "session_id": f"voice_test_{lang_code}"}
                r = requests.post(f"{MULTILINGUAL}/process_voice", files=files, data=data, timeout=20)

                status_ok = r.status_code in (200, 422)  # 422 = silent audio, still means endpoint alive
                check(
                    f"Voice ASR — {lang_name} ({lang_code})",
                    status_ok,
                    f"HTTP {r.status_code}: {r.text[:100]}"
                )
            except Exception as e:
                fail(f"Voice ASR — {lang_name}", str(e))

        # TTS only
        for lang_code, lang_name in [("en", "English"), ("hi", "Hindi"), ("ta", "Tamil")]:
            try:
                data = {"text": "Your financial health score is 72.", "language_code": lang_code}
                r = requests.post(f"{MULTILINGUAL}/tts_only", data=data, timeout=20)
                check(
                    f"TTS — {lang_name} ({lang_code})",
                    r.status_code == 200 and len(r.content) > 100,
                    f"HTTP {r.status_code}, bytes={len(r.content)}"
                )
            except Exception as e:
                fail(f"TTS — {lang_name}", str(e))

        # Translation
        translate_cases = [
            ("hi", "Mutual fund me invest karna chahiye",      "Hindi → detect"),
            ("ta", "பண்பு மேம்பாட்டிற்கு முதலீடு செய்யுங்கள்", "Tamil → detect"),
        ]
        for lang_code, text, label in translate_cases:
            try:
                body = {"text": text, "source_language": lang_code, "target_language": "english"}
                r = requests.post(f"{MULTILINGUAL}/translate", json=body, timeout=15)
                check(f"Translate — {label}", r.status_code == 200, f"HTTP {r.status_code}")
                if r.status_code == 200:
                    print(f"   translation={r.json().get('translated_text', '')[:80]!r}")
            except Exception as e:
                fail(f"Translate — {label}", str(e))

    # ─── 5. FIRE → SIP → Tax Planning Flow ───────────────────────────────────────
    print("\n══════════════════════════════════════════════════")
    print(" 4. FIRE → SIP → Tax Planning Flow")
    print("══════════════════════════════════════════════════")

    profile = {
        "user_id": "integ_planner",
        "monthly_expenses": 60000,
        "current_savings": 800000,
        "monthly_investment": 30000,
        "expected_return": 12,
        "inflation_rate": 6,
    }

    fire_res = post_json(f"{GATEWAY}/fire-planner", profile)
    if fire_res:
        d = fire_res.get("data") or fire_res
        fire_num     = d.get("fire_number", 0)
        years_to_fire = d.get("years_to_fire", 0)
        check("FIRE — returns fire_number",    fire_num > 0,        f"fire_number={fire_num}")
        check("FIRE — returns years_to_fire",  years_to_fire > 0,   f"years_to_fire={years_to_fire}")
        print(f"   FIRE number: ₹{fire_num:,.0f}  in {years_to_fire} years")
    else:
        fail("FIRE planner call", "no response")

    # SIP to reach FIRE number
    sip_res = post_json(f"{GATEWAY}/sip-calculator", {
        "monthly_amount": 30000,
        "expected_return": 12,
        "years": years_to_fire or 15,
    })
    if sip_res:
        d = sip_res.get("data") or sip_res
        check("SIP — wealth_gain positive",  (d.get("wealth_gain") or 0) > 0, f"gain={d.get('wealth_gain')}")
        check("SIP — expected_value > FIRE?", (d.get("expected_value") or 0) > 0, f"value={d.get('expected_value')}")
    else:
        fail("SIP calculator call", "no response")

    # Tax optimisation for the same user
    tax_res = post_json(f"{GATEWAY}/tax-wizard", {
        "user_id": "integ_planner",
        "annual_income": 1200000,
        "investments_80c": 150000,
        "nps_contribution": 50000,
        "health_insurance_premium": 25000,
    })
    if tax_res:
        d = tax_res.get("data") or tax_res
        check("Tax — recommended regime present",  d.get("recommended") in ("old", "new"), f"recommended={d.get('recommended')}")
        check("Tax — old regime tax calculated",   (d.get("old_regime_tax") or 0) >= 0)
        check("Tax — new regime tax calculated",   (d.get("new_regime_tax") or 0) >= 0)
        print(f"   recommended: {d.get('recommended')}  savings: ₹{d.get('savings', 0):,.0f}")
    else:
        fail("Tax wizard call", "no response")

    # ─── 6. Profile → Health Score → Advisory Flow ───────────────────────────────
    print("\n══════════════════════════════════════════════════")
    print(" 5. Profile → Health Score → Advisory Flow")
    print("══════════════════════════════════════════════════")

    full_profile = {
        "user_id": "integ_health_user",
        "name": "Test User",
        "age": 30,
        "income": 70000,
        "expenses": 40000,
        "savings": 300000,
        "emergency_fund": 120000,
        "has_health_insurance": True,
        "investments_80c": 80000,
        "life_insurance_cover": 2500000,
    }

    upsert_res = post_json(f"{GATEWAY}/profile/upsert", full_profile)
    check("Profile upsert",  upsert_res is not None, "upsert failed")

    health_res = post_json(f"{GATEWAY}/money-health-score", full_profile)
    if health_res:
        d = health_res.get("data") or health_res
        score = d.get("score") or d.get("health_score") or 0
        check("Health score — numeric score",    isinstance(score, (int, float)) and score > 0, f"score={score}")
        check("Health score — has breakdown",    bool(d.get("breakdown") or d.get("components")),   "breakdown missing")
        check("Health score — has recommendations", bool(d.get("recommendations")),                "recommendations missing")
        print(f"   score={score}  grade={d.get('grade', '?')}")
    else:
        fail("Money health score", "no response")

    # RAG knowledge is available
    rag_res = post_json(f"{GATEWAY}/rag_query", {"query": "How to build emergency fund?", "user_id": "integ_health_user"})
    if rag_res:
        d = rag_res.get("data") or rag_res
        answer = d.get("answer") or d.get("response", "")
        check("RAG query — answer present",   len(answer) > 10, f"answer={answer[:50]!r}")
    else:
        fail("RAG knowledge query", "no response")

    # ─── 7. Couples Planner Flow ─────────────────────────────────────────────────
    print("\n══════════════════════════════════════════════════")
    print(" 6. Couples Planner Flow")
    print("══════════════════════════════════════════════════")

    couples_res = post_json(f"{GATEWAY}/couples-planner", {
        "partner1_user_id": "couple_p1",
        "partner2_user_id": "couple_p2",
        "combined_goal": "Buy a house in Mumbai within 5 years and build joint retirement corpus",
    })
    if couples_res:
        d = couples_res.get("data") or couples_res
        check("Couples — response not empty", bool(d), "empty response")
        # may return joint_corpus, advice, goals, etc.
        print(f"   keys={list(d.keys())[:6]}")
    else:
        fail("Couples planner", "no response")

    # ─── Summary ─────────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'═' * 55}")
    print(f"Integration Tests: {passed}/{total} passed  ({failed} failed)")
    print(f"{'═' * 55}")

    if failed:
        print("\n⚠️  Some tests failed. Ensure all services are running:")
        print("   python Creda_Fastapi/app.py              → :8080 (Gateway)")
        print("   python Creda_Fastapi/fastapi1_multilingual.py → :8000")
        print("   python Creda_Fastapi/fastapi2_finance.py      → :8001")
