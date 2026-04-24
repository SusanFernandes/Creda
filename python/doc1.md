# CREDA `python/` — functionality: what exists, what drives it, what is weak or static

This doc is for the **Django (8000) + FastAPI (8001)** stack under `python/`, not the older **Next.js + multi-service** write-up. It focuses **feature-by-feature**: what is implemented, what numbers are based on, and where behaviour is **placeholder, default-heavy, or not truly personalised**.

---

## 1. Shared foundations (everything builds on this)

| Piece | What it is | Impact on “dynamic” behaviour |
|-------|----------------|-------------------------------|
| **User profile** | Postgres `user_profiles` + optional `portfolios` / funds from CAMS upload. | If onboarding is incomplete or fields are `0` / empty, many agents still run using **Python defaults** (very often **`monthly_income=50000`**, **`monthly_expenses=30000`**, **`age=30`**). Outputs can look “real” but are **not your data**. |
| **LLM** | **Groq** `llama-3.3-70b-versatile` (`app/core/llm.py`) for most agents + synthesiser; `llama-3.1-8b-instant` for fast intent work. | If **`GROQ_API_KEY`** is missing or rate-limited, **advice / narrative / RAG answers** degrade or go empty while some numeric shells may still return. |
| **LangGraph** | `load_profile` → **one** routed `agent_node` → `synthesizer` (`app/agents/graph.py`). | Chat and voice-pipeline use this; **direct** `/agents/...` routes call the same agent `run` functions with a constructed `FinancialState`. |
| **Chroma RAG** | HTTP Chroma; collection `creda_knowledge`; content from **`knowledge/documents.yaml`** (~23 entries, not “60+” as the RAG module comment claims). | Retrieval is real; **corpus size and legal freshness** are limited. RAG filters chunks with **distance &lt; 0.5** — can yield **“no context”** often depending on embedding similarity. |
| **Django UI** | Server-rendered templates + `BackendClient` → FastAPI. | Pages **render** even when the API returns `null` / errors (views often catch exceptions → empty context). UI can look “designed” but show **no data** or stale layout text. |

---

## 2. Feature inventory (backend + UI)

Legend: **Inputs** = what drives numbers. **Risk** = common ways it misleads.

### Auth & profile

| Feature | Implemented? | Inputs | Risk / gaps |
|---------|----------------|--------|-------------|
| Register / login (Django + FastAPI user) | Yes | Email, password | Must run **Django migrations** on `creda_django` (`auth_user`, `django_session`). |
| Profile CRUD | Yes | Form / onboarding JSON | **`savings`** column is separate from “income − expenses”; not always auto-synced. Many agents **ignore** `profile.savings` and derive flow from income/expenses instead. |

### Dashboard & settings

| Feature | Implemented? | Inputs | Risk / gaps |
|---------|----------------|--------|-------------|
| Dashboard cards (income, surplus, emergency, risk) | Yes | Profile API + `monthly_surplus` computed server-side | Marketing labels (“Active”, “Tracking”) are **static**. If profile 404, redirect to onboarding. |
| Settings HTMX save | Yes | Posted fields | Only a **subset** of profile fields is on the settings form vs full schema. |

### Portfolio (CAMS)

| Feature | Implemented? | Inputs | Risk / gaps |
|---------|----------------|--------|-------------|
| PDF upload + parse | Yes | **casparser** on PDF bytes | Password-protected PDFs need correct password. Parse failures → upload error. |
| Per-scheme XIRR | Yes (when transactions exist) | **pyxirr** on casparser cashflows | Missing/odd transactions → `0` XIRR common. |
| Fund “category” | Partial | **Heuristic** `_classify_category` from scheme name/type | Not AMC official sector data. |
| Expense ratio on holdings | **Estimated** | `_estimate_expense_ratio` by category + direct/regular flag | **Not** pulled from live TER feed — numbers are **illustrative**. |
| X-Ray report | Yes | Aggregates + **Groq** for rebalance text | Overlap = “same category string appears &gt; once” — simplistic vs real overlap engines. |

### FIRE planner (`/agents/fire-planner`)

| Implemented? | Yes |
| Inputs | Profile: income, expenses, age, `fire_target_age`, savings, EPF/NPS/PPF; portfolio `current_value`; fixed **6% inflation**, **6% real return** (12% nominal − 6% inflation), **4% rule** for FIRE number; roadmap uses **10% annual SIP step-up**. |
| **Not proper / static** | Return and inflation are **hardcoded**, not user-tuned or market-linked. **`current_sip = income − expenses`** — not the same as the DB **`savings`** field. If income/expense missing in DB, **₹50k / ₹30k defaults** drive the whole plan. |
| LLM | Adds narrative from computed `data` dict | If Groq fails, `advice` string empty but numbers still show. |

### Tax wizard (`/agents/tax-wizard`)

| Implemented? | Yes (FY2024-25 style slabs in code) |
| Inputs | Annualised `monthly_income * 12`, 80C/80D/NPS/HRA/rent, city for metro HRA %, assumed **`basic_salary = 40% of gross`** if HRA logic runs. |
| **Not proper** | **Not a full ITR engine**: simplified slabs/rebates; many real-life sections not modelled. **`rent_paid`**, **`parents_health_premium`** etc. are often **never collected** in onboarding → treated as 0 → HRA / parent 80D wrong. |
| LLM | Narrative on top of computed dict | Same Groq dependency. |

### SIP calculator (`/agents/sip-calculator`)

| Implemented? | Yes |
| Inputs | Income, expenses → “available” SIP; optional target/years parsed from **chat message regex** only on chat path; direct page call uses defaults in `run` (target = **25× annual income**, years **20**) when message empty. |
| **Static / wrong** | **12% CAGR** and **10% step-up** are **fixed**. Not personalised risk profile. Direct HTTP agent call from dashboard **does not pass user-typed goal** in the JSON body (only `language`) — so the **page can show a generic projection**, not “your crore target from the form” unless chat intent passes it in text. |

### Budget coach

| Implemented? | Yes |
| Inputs | Income, expenses, EMI | **50/30/20** “actuals” are crude: **`needs = expenses − EMI`**, **`wants = EMI`** — not real category spend. |
| LLM | Commentary | Defaults **50k/30k** if profile empty. |

### Money health

| Implemented? | Yes (weighted 6 dimensions) |
| Inputs | Profile + portfolio fund list | Several dimensions are **rules of thumb** (e.g. diversification = **count of distinct category strings**). Retirement score uses **`fire_corpus_target`** or a **rough age heuristic**. Defaults **50k/30k** if missing. |
| LLM | “Top 3 actions” | Can be empty if Groq fails. |

### Stress test

| Implemented? | Yes |
| Inputs | Profile + portfolio value; events from UI list or message detection | **`ITERATIONS = 500`** Monte Carlo with **Python `random`** — not numpy vectorised doc claims; distribution assumptions are **simplified** in `_monte_carlo`. Fixed event costs (e.g. baby **₹25k/mo**). |
| LLM | Mitigation bullets | — |

### Goal planner

| Implemented? | Yes |
| Inputs | Income, expenses; goals from **message parsing** `_extract_goals` | Returns depend heavily on **user wording in chat**. Fixed **8% / 12%** return by horizon. |

### Couples finance

| Implemented? | Yes |
| Inputs | User profile + partner income/expense from API body | Partner defaults to 0 if not sent; user side still **50k/30k** defaults if profile thin. |

### Market pulse

| Implemented? | Partial |
| Inputs | **RSS** (ET, Moneycontrol) + **yfinance** for Nifty/Sensex + user portfolio summary | Feeds/network can fail → **fallback headline**. LLM may still “sound” confident. |

### Tax copilot, money personality, goal simulator, ET research, human handoff, family wealth

| Implemented? | Yes (routes + agent modules exist) |
| Inputs | Mostly profile + (where relevant) portfolio / message | Same pattern: **defaults**, **simplified rules**, **Groq narrative**. Each should be reviewed individually before claiming regulatory or psychological accuracy. |

### Social proof

| Implemented? | Yes |
| Inputs | If **≥5** completed profiles in age band → **SQL averages**; else **`_FALLBACK_BENCHMARKS`** dict | For most dev/small installs you see **curated static peer stats** and sample_size 0 — **not real crowd data**. |

### RAG / regulatory Q&A

| Implemented? | Yes |
| Inputs | Chroma top-k + Groq | Small YAML corpus; distance threshold; comment overstates doc count. |

### Chat (main)

| Implemented? | Yes |
| Inputs | Intent cascade + LangGraph + Redis history + Postgres messages | Quality = intent + agent + profile completeness. |

### Voice

| Implemented? | Yes |
| Inputs | **faster-whisper** STT → same agent path as chat → **Kokoro / Edge / Piper / gTTS** | Not the IndicConformer / Parler stack from the old architecture doc. Latency/quality vary by machine. |

### Nudges & notifications

| Implemented? | Yes |
| Inputs | APScheduler + `nudge_worker` logic reading profile | Content is **template/rules**, not personalised push from external market data unless coded there. |

### WhatsApp webhook

| Implemented? | Partial (Twilio-form webhook exists) | End-to-end product flow not covered here. |

### Compliance endpoints

| Implemented? | Yes | Report generation depends on stored logs / profile — depth should be validated separately. |

---

## 3. Summary: what is “not working yet” in a product sense

1. **No single source of financial truth for defaults** — Many agents assume **₹50,000 / ₹30,000** income and expenses when the DB has zeros. The UI can show charts while maths is **generic middle-class placeholders**.  
2. **Tax, FIRE, SIP, goals are illustrative calculators**, not audited tax software or advisory-grade Monte Carlo.  
3. **Portfolio expense ratio and categories** are partly **estimated / heuristic**, not live AMFI facts.  
4. **Social proof** is usually **static benchmarks** until you have enough real users in Postgres.  
5. **SIP / goal targets from dedicated dashboard pages** may not pass rich parameters into the agent — behaviour is **chat-oriented** for some parsers.  
6. **RAG** is limited corpus + strict relevance filter — expect **“not in knowledge base”** often.  
7. **Landing and chrome around the app** remain **marketing / static** regardless of backend quality.

---

## 4. What you should do to make outputs “more dynamic”

1. Complete **onboarding** (real income, expenses, age, tax-related fields you care about).  
2. **Upload CAMS** before trusting portfolio-linked agents.  
3. Set **`GROQ_API_KEY`** in `python/.env`.  
4. For SIP/goal specificity, use **chat** with explicit amounts (“1 crore in 15 years”) or extend the dashboard POST bodies to send those fields into FastAPI.  
5. Treat all numbers as **educational estimates** until models and data pipelines are upgraded.

---

*Aligned with code in `python/backend/app/agents`, `routers`, and `frontend/dashboard` as of the doc date. Update when agents or defaults change.*
