# CREDA `python/` stack — what works vs what the UI implies

This document describes the **Django + FastAPI monorepo under `python/`** (ports **8000** frontend, **8001** API by default). It is **not** the same layout as DOC 1’s three-service design (gateway **8080**, multilingual **8000**, finance **8001** with separate `app.py` / `fastapi1_multilingual.py` / `fastapi2_finance.py`). DOC 2 impact numbers and **key assumptions are out of scope** here.

---

## 1. Architecture comparison (DOC 1 vs this repo)

| DOC 1 concept | In `python/` today |
|---------------|-------------------|
| Single API gateway (8080) | **Not implemented.** Browser hits Django (`:8000`) and Django’s `BackendClient` calls FastAPI (`:8001`). |
| Multilingual microservice on 8000 | **No.** Port **8000** is **Django + Daphne** serving HTML, not a standalone ASR/LLM/TTS microservice. |
| Finance service on 8001 | **Yes (conceptually):** FastAPI on **8001** hosts agents, chat, portfolio, voice, etc. |
| SQLModel + SQLite | **No.** **PostgreSQL** (`creda_api` / `creda_django`) + **SQLAlchemy** (async) + **Alembic** (API side). |
| ChromaDB + ~52 regulatory chunks | **Partial.** Knowledge is **`backend/knowledge/documents.yaml`** with **23 curated entries** (not 52 PDFs). Loaded into Chroma on startup if empty. |
| IndicConformer ASR, Indic Parler-TTS, IndicTrans2 | **Not implemented.** STT: **faster-whisper** (+ Groq Whisper fallback). TTS: **Kokoro → Edge → Piper → gTTS** chain. |
| LangGraph “6 specialist agents” | **Different shape:** one **LangGraph** (`agents/graph.py`: load profile → **one** routed agent node → synthesizer) with **many** intent→module mappings (portfolio, stress, FIRE, tax, money health, budget, goals, couples, SIP, RAG, onboarding, general, plus ET-style agents, etc.). |
| Twilio voice `/twilio/brain` | **Not the same.** There is a **`/whatsapp/webhook`** Twilio-style handler for WhatsApp; full voice brain parity with DOC 1 is **not** documented here. |
| Next.js / Expo clients | **No.** **Django templates** + HTMX/fetch to `/api/*` proxies only. |

---

## 2. What is working (backend + wired frontend)

These paths are **implemented** and generally **functional** when Postgres, Redis, Chroma (optional), and `GROQ_API_KEY` are available:

- **Auth:** Django register/login/logout; FastAPI `/auth/register`, `/auth/token`; JWT + `backend_user_id` session link for API calls.
- **Profile:** `/profile/upsert`, `/profile/{id}` — persisted in **`user_profiles`** (Postgres `creda_api`).
- **Chat:** `/chat` — intent cascade → **LangGraph** `run_agent` → Redis history + Postgres `conversation_messages`.
- **Agents (direct POST `/agents/...`):** fire-planner, tax-wizard, money-health, stress-test, budget-coach, goal-planner, couples-finance, sip-calculator, market-pulse, tax-copilot, money-personality, goal-simulator, social-proof, et-research, human-handoff, family-wealth (each calls real Python agent modules; quality depends on Groq + prompts + data).
- **Portfolio:** CAMS PDF **upload** + DB persistence; **xray** on stored portfolio (uses parsed funds + LLM-style analysis).
- **Voice:** `/voice/transcribe`, `/voice/speak`, `/voice/pipeline` (STT → agent/chat path → TTS).
- **Nudges:** `/nudges/pending`, read endpoints; scheduler jobs in FastAPI lifespan.
- **Compliance:** compliance report + AI disclosure endpoints.
- **Family:** members + link + family-wealth agent.
- **Health:** FastAPI `/health` checks Postgres, Redis, Chroma, TTS URLs.
- **Django pages** that call the above via `request.backend.*`: dashboard (profile + nudges), settings (save), onboarding (profile upsert), chat, portfolio upload/xray, health, fire, tax, budget, goals, stress-test, couples, SIP, market pulse, tax copilot, personality, goal simulator, social proof, research, voice, advisor handoff, compliance, family, notifications.

---

## 3. Frontend: what looks real but is mostly static or marketing

| Location | What users see | Reality |
|----------|----------------|--------|
| **`landing.html`** | Hero copy, “Trusted by investors across India”, feature lists, stats, FAQ | **Static marketing.** Not fed by analytics or live user counts. |
| **`login.html`** (left column) | Product pitch, feature bullets | **Static.** |
| **Dashboard cards** | Copy like “Active”, “Tracking”, “Calibrated” | **Decorative labels** next to real numbers where profile exists. |
| **Any agent page when API fails** | Often empty sections or minimal content | Views **swallow errors** (`try/except` → `None`); UI may look “blank” rather than “error”. |
| **“Trusted by…” / pulse badges** | Green pulse dots | **Visual only**, not connectivity to real-time telemetry. |

---

## 4. Not implemented vs DOC 1 (or partially implemented)

| DOC 1 / expectation | In `python/` |
|---------------------|--------------|
| **8080 API gateway** with subprocess-orchestrated trio | **Absent.** |
| **Dedicated multilingual service** (22 langs ASR, Indic TTS, translation stack) | **Absent** as a service; language is passed as a string into agents/voice with **different** engines. |
| **SQLite + SQLModel** finance DB | **Absent** — **Postgres** + SQLAlchemy models. |
| **52-document** regulatory corpus in Chroma | **~23 YAML topics**, not the same corpus or count. |
| **Monte Carlo “500 sims”** etc. as specified | Stress agent exists; **implementation detail may differ** from DOC numbers—verify `stress_test.py` if you need exact parity. |
| **CAMS parse fallbacks** (pdfplumber chain) | **casparser-centred** path in code; full multi-tier fallback table from DOC 1 **not** mirrored 1:1. |
| **Twilio voice brain** route | **WhatsApp webhook** exists; **not** the same as DOC’s `/twilio/brain` flow. |
| **ET PS9** as separate product layer | **Not** a separate deployable in this folder; some “ET-inspired” agents are names/features only. |
| **Paid tier / freemium gates** (DOC 2 style) | **Not** implemented in this repo’s UI/API. |
| **Performance SLOs** in DOC 1 tables | **Not** enforced or measured in-app. |

---

## 5. “Should work like X but doesn’t” (common pitfalls)

1. **Data “disappears” after restart**  
   - Profile/users live in **Postgres volumes**. **`docker compose down -v`**, **`make nuke`**, or **`make postgres-volume-reset`** wipe that data.  
   - After a **new** Postgres, you must run **`make migrate`** (Django **and** Alembic) or you get missing tables (`auth_user`, `django_session`, etc.).

2. **Django shows a page but numbers are wrong**  
   - Example fixed earlier: template must not misuse Django filters (e.g. **`add`** for income−expenses). Prefer API-computed fields like **`monthly_surplus`** from the backend serializer.

3. **Onboarding “saved” but nothing in DB**  
   - If `/api/profile/upsert/` fails (backend down, 401), the UI should **not** redirect; failures must be visible. Always confirm FastAPI is up for saves.

4. **Sessions**  
   - Django uses **database sessions** → requires **`django_session`** table (**migrate**).  

5. **DOC 1 client ports**  
   - Anything hard-coded for **8080 / Next.js** does not apply; this stack is **8000 + 8001**.

---

## 6. Quick “is it dynamic?” checklist for QA

| Page | Dynamic? | Notes |
|------|----------|--------|
| Dashboard | **Yes** | Profile + nudges from API. |
| Settings | **Yes** | HTMX/form POST → upsert. |
| Onboarding | **Yes** | fetch → upsert. |
| Chat | **Yes** | `/api/chat` → FastAPI. |
| Portfolio upload / xray | **Yes** | Needs valid PDF + backend. |
| Fire / Tax / Budget / Goals / Stress / … | **Yes** if backend returns JSON | **Empty** if exception or missing profile. |
| Landing / login marketing | **No** | Static HTML. |

---

*Generated from repository inspection (`backend/app`, `frontend/templates`, `docker-compose`, `knowledge/documents.yaml`). Update this file when major features or ports change.*
