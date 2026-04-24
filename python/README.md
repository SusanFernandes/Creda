<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-0.2-FF6F00?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
</p>

<h1 align="center">CREDA</h1>
<h3 align="center">AI-Powered Financial Coach for India</h3>
<p align="center">
  Multilingual voice & text financial advisor with 21+ specialized AI agents,<br>
  4-tier intent classification (keyword → embeddings → LLM), SEBI-compliant advice logging,<br>
  family wealth management, couples finance, and proactive nudges — built for every Indian household.
</p>

---

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
  - [High-Level Architecture](#high-level-architecture)
  - [Request Flow](#request-flow)
  - [Agent Pipeline](#agent-pipeline)
  - [Voice Pipeline](#voice-pipeline)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [All 22 AI Agents](#all-22-ai-agents)
  - [Core Agents](#core-agents)
  - [Intelligence Agents](#intelligence-agents)
  - [Support Agents](#support-agents)
  - [Compliance \& Infrastructure](#compliance--infrastructure)
- [| **APScheduler Jobs** | 3 scheduled jobs — daily nudges (9 AM), periodic nudges (every 6h), pre-market briefing (9:15 AM) |](#-apscheduler-jobs--3-scheduled-jobs--daily-nudges-9-am-periodic-nudges-every-6h-pre-market-briefing-915-am-)
- [Database Schema](#database-schema)
  - [creda\_api (FastAPI — Alembic migrations)](#creda_api-fastapi--alembic-migrations)
  - [creda\_django (Django — Django ORM migrations)](#creda_django-django--django-orm-migrations)
- [API Endpoints](#api-endpoints)
  - [Authentication (`/api/auth`)](#authentication-apiauth)
  - [Chat (`/api/chat`)](#chat-apichat)
  - [Voice (`/api/voice`)](#voice-apivoice)
  - [Portfolio (`/api/portfolio`)](#portfolio-apiportfolio)
  - [Agents (`/api/agents`)](#agents-apiagents)
  - [Profile (`/api/profile`)](#profile-apiprofile)
  - [Nudges (`/api/nudges`)](#nudges-apinudges)
  - [WhatsApp (`/api/whatsapp`)](#whatsapp-apiwhatsapp)
  - [Compliance (`/api/compliance`)](#compliance-apicompliance)
  - [Family (`/api/family`)](#family-apifamily)
  - [Health](#health)
  - [Budget \& Expenses (`/api/budget`)](#budget--expenses-apibudget)
  - [Export (`/api/export`)](#export-apiexport)
  - [Admin (`/api/admin`)](#admin-apiadmin)
- [Frontend Pages](#frontend-pages)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [Demo Accounts](#demo-accounts)
  - [Manual Setup](#manual-setup)
  - [Docker Compose (Production)](#docker-compose-production)
- [Makefile Commands](#makefile-commands)
- [Environment Variables](#environment-variables)
- [Design System](#design-system)
- [Intent Classification Engine](#intent-classification-engine)
- [Knowledge Base](#knowledge-base)
- [Contributing](#contributing)

---

## Overview

**CREDA** (Credit + Advice) is a full-stack AI financial coaching platform purpose-built for India. It combines LangGraph-orchestrated AI agents, real-time CAMS mutual fund analysis, voice interaction in 11 Indian languages, and proactive financial nudges to deliver personalised, actionable financial guidance.

Users interact via a premium web dashboard (text or voice) or WhatsApp. Every query is classified, routed to the right specialist agent, and synthesized into natural-language advice in the user's preferred language.

---

## Key Features

| Category | Features |
|----------|----------|
| **AI Agents** | 21+ specialized LangGraph agents covering portfolio analysis, FIRE planning, tax optimization, budgeting, goals, couples finance, life event advising, stress testing, family wealth, and more |
| **Intent Classification** | Production-grade 4-tier cascade — follow-up detection (0ms) → weighted keyword scoring (0ms) → MiniLM embedding similarity (~10ms, offline) → LLM classifier (1-2s) — saves ~95% of LLM API calls |
| **Multilingual** | Full support for 11 languages — English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Urdu |
| **Voice** | Speech-to-text (faster-whisper / Groq Whisper), text-to-speech (Kokoro / Edge TTS / Piper / gTTS), full voice pipeline |
| **Portfolio Analysis** | CAMS PDF statement parsing, fund-level X-ray, category classification, expense ratio estimation, XIRR calculation |
| **Proactive Nudges** | APScheduler-driven reminders — SIP dates, emergency fund gaps, insurance warnings, tax deadlines |
| **WhatsApp** | Twilio integration for full conversational AI via WhatsApp |
| **RAG** | ChromaDB knowledge base with 26 curated Indian financial documents (government schemes, tax rules, investment guides) |
| **SEBI Compliance** | Every AI recommendation logged with compliance audit trail, regulatory cross-referencing |
| **Family Wealth** | Multi-member family dashboard with linked portfolios and consolidated analysis |
| **Landing Page** | Professional public landing page with feature showcase, trust badges, and CTAs |
| **Premium UI** | Glassmorphism design, dark mode, responsive sidebar, HTMX partials, Alpine.js interactivity |

---

## Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           CLIENTS                                    │
│                                                                      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│   │  Browser  │    │  Mobile  │    │ WhatsApp │    │  Voice   │     │
│   │  (HTMX)  │    │  (API)   │    │ (Twilio) │    │  (Mic)   │     │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘     │
│        │               │               │               │            │
└────────┼───────────────┼───────────────┼───────────────┼────────────┘
         │               │               │               │
         ▼               ▼               ▼               ▼
┌─────────────────┐              ┌─────────────────────────────────────┐
│  Django Frontend │              │         FastAPI Backend             │
│    (port 8000)   │─── HTTP ───▶│           (port 8001)               │
│                  │              │                                     │
│  • SSR Templates │              │  ┌──────────────────────────┐      │
│  • HTMX Partials │              │  │   Intent Classification   │      │
│  • Alpine.js     │              │  │  (Keyword → LLM fallback) │      │
│  • Auth/Sessions │              │  └────────────┬─────────────┘      │
│  • BackendClient │              │               │                    │
│    Middleware     │              │               ▼                    │
└─────────────────┘              │  ┌──────────────────────────┐      │
                                  │  │    LangGraph Pipeline     │      │
                                  │  │                          │      │
                                  │  │  load_profile → agent    │      │
                                  │  │       → synthesizer      │      │
                                  │  │                          │      │
                                  │  │  21+ Specialist Agents   │      │
                                  │  └──────────────────────────┘      │
                                  └──────────┬──────────────────────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
                          ▼                  ▼                  ▼
                   ┌────────────┐    ┌────────────┐    ┌────────────┐
                   │ PostgreSQL │    │   Redis    │    │  ChromaDB  │
                   │  (2 DBs)   │    │  (Cache)   │    │   (RAG)    │
                   └────────────┘    └────────────┘    └────────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
                          ▼                  ▼                  ▼
                   ┌────────────┐    ┌────────────┐    ┌────────────┐
                   │ Kokoro TTS │    │ Piper TTS  │    │Groq / LLaMA│
                   │  (Voice)   │    │ (Fallback) │    │   (LLM)    │
                   └────────────┘    └────────────┘    └────────────┘
```

### Request Flow

```
User Message
    │
    ▼
┌───────────────────┐
│  Django Frontend   │  ← Handles auth, sessions, template rendering
│  BackendClient     │  ← Async HTTP proxy to FastAPI
└─────────┬─────────┘
          │ POST /api/chat  (with JWT + user-id headers)
          ▼
┌───────────────────┐
│  FastAPI Router    │
│  /chat endpoint    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────────────────────────────────────────────┐
│          4-Tier Intent Classification Cascade              │
│                                                           │
│  Tier 1: Follow-up Detection (0ms)                        │
│    • "yes", "tell me more", "हाँ", "ஆம்"                │
│    • Short phrases → reuse last agent (from Redis)        │
│    • Avoids reclassification on continuations              │
│                                                           │
│  Tier 2: Weighted Keyword Scoring (0ms)                   │
│    • 70+ regex patterns × 22 intents                      │
│    • Each keyword has specificity weight (1.0 → 3.0)      │
│    • Supports 8 Indian languages                          │
│    • Resolves ambiguity via score gap (top − 2nd place)   │
│                                                           │
│  Tier 3: Embedding Similarity (~10ms, offline, CPU)       │
│    • all-MiniLM-L6-v2 (87MB, runs locally)                │
│    • 22 intent centroids from curated trigger phrases     │
│    • Cosine similarity ≥ 0.78 → route directly            │
│    • Catches natural phrasing: "help me plan for the      │
│      future" → fire_planner                               │
│                                                           │
│  Tier 4: LLM Classifier (1-2s, safety net)                │
│    • Groq llama-3.1-8b (fast, cheap)                      │
│    • Receives hints from Tiers 2-3 to disambiguate        │
│    • Only reached for ~5% of queries                      │
└────────────┬──────────────────────────────────────────────┘
             │ intent
             ▼
┌───────────────────────────────────────────────┐
│              LangGraph Pipeline                │
│                                                │
│  [load_profile] → [agent_dispatch] → [synth]  │
│                                                │
│  load_profile:                                 │
│    • Fetch UserProfile + Portfolio from DB      │
│    • Inject into state                          │
│                                                │
│  agent_dispatch:                                │
│    • Route to 1 of 22 agents via _AGENT_MAP    │
│    • Agent writes structured output to state   │
│                                                │
│  synthesizer:                                   │
│    • Converts agent output → natural language  │
│    • Respects user's language preference        │
│    • Voice mode = shorter (200 words)           │
│    • Text mode = richer (300 words)             │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
              Final response (text + language)
              Saved to Redis (cache) + PostgreSQL (permanent)
```

### Agent Pipeline

```
                    ┌─────────────────┐
                    │   FinancialState │
                    │                 │
                    │  user_id        │
                    │  message        │
                    │  intent  ───────┼──────────────────────────────┐
                    │  language       │                              │
                    │  voice_mode     │                              │
                    │  history        │                              │
                    └────────┬────────┘                              │
                             │                                       │
                    ┌────────▼────────┐                              │
                    │  load_profile   │                              │
                    │  (DB lookup)    │                              │
                    └────────┬────────┘                              │
                             │                                       │
                    ┌────────▼────────┐                              │
                    │ agent_dispatch  │◀─────────────────────────────┘
                    │                 │
                    │  _AGENT_MAP:    │
                    │  ┌────────────────────────────────────┐
                    │  │ portfolio_xray  │ stress_test      │
                    │  │ fire_planner    │ tax_wizard       │
                    │  │ money_health    │ budget_coach     │
                    │  │ goal_planner    │ couples_finance  │
                    │  │ sip_calculator  │ market_pulse     │
                    │  │ tax_copilot     │ money_personality│
                    │  │ goal_simulator  │ social_proof     │
                    │  │ et_research     │ human_handoff    │
                    │  │ rag_query       │ onboarding       │
                    │  │ family_wealth   │ general_chat     │                    │  │ expense_analytics│ life_event_advisor│                    │  └────────────────────────────────────┘
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   synthesizer   │
                    │                 │
                    │  LLM formats    │
                    │  agent output   │
                    │  into natural   │
                    │  language       │
                    └────────┬────────┘
                             │
                             ▼
                    Final response string
```

### Voice Pipeline

```
┌────────┐     ┌──────────────┐     ┌───────────────┐     ┌─────────────┐
│  User  │────▶│   STT Engine │────▶│  Chat Pipeline │────▶│  TTS Engine │
│  Mic   │     │              │     │  (as above)    │     │             │
└────────┘     │ 1. faster-   │     └───────────────┘     │ 1. Kokoro   │
               │    whisper   │                           │ 2. Edge TTS │
               │ 2. Groq      │                           │ 3. Piper    │
               │    Whisper   │                           │ 4. gTTS     │
               └──────────────┘                           └──────┬──────┘
                                                                  │
                       ┌──────────────────────────────────────────┘
                       ▼
              Audio response (WAV)
              + X-Transcript header
              + X-Response-Text header
              + X-Intent header
              + X-Language header
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Intent Classification** | sentence-transformers/all-MiniLM-L6-v2 | Tier 3 embedding-based intent matching (local, offline) |
| **LLM** | Groq (LLaMA 3.3 70B + LLaMA 3.1 8B) | Agent reasoning + synthesis |
| **Agent Framework** | LangGraph | Stateful multi-agent orchestration |
| **Backend API** | FastAPI + Uvicorn (async) | REST API, WebSocket, SSE |
| **Frontend** | Django 5.1 + Daphne (ASGI) | SSR, auth, session management |
| **UI Interactivity** | HTMX + Alpine.js | Partial updates, client state |
| **CSS** | Tailwind CSS (CDN) | Utility-first styling |
| **Database** | PostgreSQL 15 | Dual-database (api + django) |
| **Cache** | Redis 7 | Conversation cache, rate limiting |
| **Vector DB** | ChromaDB | RAG knowledge base |
| **STT** | faster-whisper / Groq Whisper API | Speech to text |
| **TTS** | Kokoro / Edge TTS / Piper / gTTS | Text to speech (4-tier fallback) |
| **PDF Parsing** | casparser | CAMS mutual fund statements |
| **XIRR** | pyxirr | Portfolio return calculation |
| **Scheduling** | APScheduler | Proactive nudge generation |
| **WhatsApp** | Twilio API | WhatsApp channel |
| **Market Data** | yfinance + feedparser | Real-time indices & news |
| **Containerization** | Docker Compose | 7-service orchestration |

---

## Project Structure

```
python/
├── Makefile                    # PowerShell-native dev commands
├── docker-compose.yml          # 7-service orchestration
├── .env.example                # Environment template
├── pyproject.toml              # Project metadata
├── models/                     # ML models (gitignored, downloaded by `make init`)
│   └── all-MiniLM-L6-v2/      # ~87MB sentence-transformers model for Tier 3
│
├── docker/
│   └── init-databases.sh       # Creates creda_api + creda_django DBs
│
├── backend/                    # ── FastAPI Backend (port 8001) ──
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              # Async Alembic config
│   │   └── versions/           # Migration files
│   │
│   ├── app/
│   │   ├── main.py             # FastAPI app, lifespan, CORS, scheduler
│   │   ├── config.py           # Env-driven settings (pydantic)
│   │   ├── database.py         # Async SQLAlchemy engine + session
│   │   ├── models.py           # 16 SQLAlchemy models
│   │   ├── auth.py             # JWT creation + verification
│   │   ├── redis_client.py     # Redis connection
│   │   │
│   │   ├── core/
│   │   │   └── llm.py          # Groq LLM singletons (70B + 8B)
│   │   │
│   │   ├── agents/             # ── 22 LangGraph Agents ──
│   │   │   ├── state.py        # FinancialState TypedDict
│   │   │   ├── graph.py        # LangGraph pipeline + _AGENT_MAP
│   │   │   ├── synthesizer.py  # Natural language synthesis
│   │   │   ├── intent_router.py # LLM intent classifier
│   │   │   ├── portfolio_xray.py
│   │   │   ├── stress_test.py
│   │   │   ├── fire_planner.py
│   │   │   ├── tax_wizard.py
│   │   │   ├── money_health.py
│   │   │   ├── budget_coach.py
│   │   │   ├── goal_planner.py
│   │   │   ├── couples_finance.py
│   │   │   ├── sip_calculator.py
│   │   │   ├── general_chat.py
│   │   │   ├── onboarding.py
│   │   │   ├── rag_agent.py
│   │   │   ├── market_pulse.py      # Real-time market data
│   │   │   ├── tax_copilot.py       # Live tax optimization
│   │   │   ├── money_personality.py # Behavioral analysis
│   │   │   ├── goal_simulator.py    # Monte Carlo simulation
│   │   │   ├── social_proof.py      # Peer benchmarking
│   │   │   ├── et_research.py       # Financial research engine
│   │   │   ├── human_handoff.py     # Advisor escalation
│   │   │   ├── family_wealth.py     # Family wealth management
│   │   │   ├── life_event_advisor.py # Life event bonus/windfall advisor
│   │   │   └── expense_analytics.py  # Expense analytics & tracking
│   │   │
│   │   ├── routers/            # ── FastAPI Routers ──
│   │   │   ├── auth.py         # Login / register (rate-limited)
│   │   │   ├── chat.py         # Chat + SSE streaming
│   │   │   ├── voice.py        # STT / TTS / full pipeline
│   │   │   ├── portfolio.py    # Upload / X-ray / summary
│   │   │   ├── agents.py       # Direct agent endpoints (17)
│   │   │   ├── profile.py      # Profile CRUD
│   │   │   ├── nudges.py       # Nudge management
│   │   │   ├── whatsapp.py     # Twilio webhook
│   │   │   ├── compliance.py   # SEBI compliance & AI disclosure
│   │   │   ├── family.py       # Family linking & members
│   │   │   ├── budget.py       # Budget & expense CRUD
│   │   │   ├── admin.py        # Admin stats & user management
│   │   │   ├── export.py       # CSV/PDF report generation
│   │   │   └── ws.py           # WebSocket real-time updates
│   │   │
│   │   └── services/           # ── Business Services ──
│   │       ├── intent_engine.py      # 4-tier cascade orchestrator
│   │       ├── intent_classifier.py  # Tier 2: weighted keyword scoring
│   │       ├── intent_embeddings.py  # Tier 3: MiniLM embedding matcher
│   │       ├── stt.py               # Speech-to-text (whisper/groq)
│   │       ├── tts.py               # Text-to-speech (4-tier)
│   │       ├── nudge_worker.py      # APScheduler nudge jobs
│   │       ├── compliance.py        # SEBI advice logging
│   │       └── rag.py               # ChromaDB loader
│   │
│   └── knowledge/
│       └── documents.yaml      # 26 curated Indian financial docs
│
└── frontend/                   # ── Django Frontend (port 8000) ──
    ├── Dockerfile
    ├── requirements.txt
    ├── manage.py
    │
    ├── creda/                  # Django project config
    │   ├── settings.py         # Database, middleware, templates
    │   ├── urls.py             # Root URL conf
    │   ├── middleware.py       # BackendClient (28+ typed API methods)
    │   ├── asgi.py             # ASGI application
    │   └── wsgi.py             # WSGI fallback
    │
    ├── accounts/               # Auth app
    │   ├── models.py           # Custom User (extends AbstractUser)
    │   ├── views.py            # landing, login, register, logout (async)
    │   ├── urls.py             # /, /login/, /register/, /logout/
    │   └── admin.py            # Django admin registration
    │
    ├── dashboard/              # Main app
│   │   ├── views.py            # 30 async views + API proxies
│   │   ├── urls.py             # 52 URL patterns (34 pages + 18 API proxies)
│   │   └── templatetags/       # Custom Django template filters
│   │       ├── __init__.py
│   │       └── creda_filters.py # strip_markdown, indian_number, humanize_key, to_json
    │
    ├── static/css/
    │   └── app.css             # Custom overrides
    │
    └── templates/
        ├── base.html           # Root template (Tailwind, Alpine, HTMX)
        ├── base_dashboard.html # Sidebar layout (28 nav links, dark mode, language switcher)
        ├── landing.html        # Public landing page (professional)
        ├── accounts/
        │   ├── login.html
        │   └── register.html
        └── dashboard/
            ├── dashboard.html
            ├── chat.html
            ├── portfolio.html
            ├── health.html
            ├── fire.html
            ├── tax.html
            ├── budget.html
            ├── goals.html
            ├── stress_test.html
            ├── settings.html
            ├── onboarding.html
            ├── notifications.html
            ├── couples.html
            ├── sip_calculator.html
            ├── market_pulse.html
            ├── tax_copilot.html
            ├── money_personality.html
            ├── goal_simulator.html
            ├── social_proof.html
            ├── research.html
            ├── voice.html
            ├── expense_analytics.html
            ├── life_events.html
            ├── compliance.html
            ├── family.html
            ├── admin.html
            ├── advisor.html
            ├── report_card.html
            └── partials/
                ├── health_content.html
                ├── market_pulse_content.html
                ├── upload_result.html
                ├── xray_result.html
                └── refresh_result.html
```

---

## All 22 AI Agents

### Core Agents

| Agent | Purpose | Key Inputs |
|-------|---------|------------|
| **Portfolio X-Ray** | Parse CAMS PDF, classify funds (15 categories), estimate expense ratios, compute XIRR, detect overlap | PDF upload |
| **Stress Test** | Monte Carlo simulation across scenarios (job loss, medical emergency, market crash, recession, retirement) | Events selection |
| **FIRE Planner** | Financial Independence Retire Early analysis — FIRE number, savings rate, years to FIRE, tax gaps | Profile data |
| **Tax Wizard** | Old vs New regime comparison, HRA exemption (metro-aware), 80C/80D/80CCD deductions, missed opportunities | Profile + income data |
| **Money Health** | 0–100 health score across 6 dimensions — savings, debt, insurance, emergency fund, investment, planning | Profile data |
| **Budget Coach** | 50/30/20 rule analysis — needs, wants, savings split with category breakdowns | Profile + expenses |
| **Goal Planner** | Goal-based SIP calculator — education, house, retirement, marriage with inflation-adjusted targets | Goals + timeline |
| **Couples Finance** | Joint financial analysis — combined income/expenses, savings rate, optimal split strategy | Both partners' data |
| **SIP Calculator** | Monthly SIP projections with step-up, multiple return scenarios (Conservative/Moderate/Aggressive) | Amount + horizon |

### Intelligence Agents

| Agent | Purpose | Key Inputs |
|-------|---------|------------|
| **Market Pulse** | Real-time Nifty 50, Sensex, Bank Nifty, Nifty IT indices + financial news headlines + portfolio impact | Portfolio data |
| **Tax Copilot** | Live deduction tracker (section-wise utilization %), tax-loss harvesting opportunities, deadline reminders | Profile + portfolio |
| **Money Personality** | Behavioral archetype analysis (Saver/Spender/Investor/Avoider/Giver/Risk-Taker), dimension scoring, blind spots | Profile + spending |
| **Goal Simulator** | Monte Carlo goal simulation — 3 scenarios (Conservative P10/Moderate P50/Aggressive P90), year-by-year projection | Target + years |
| **Social Proof** | Peer benchmarking — savings rate, SIP amount, net worth vs age group averages + India-wide percentile | Profile + age |
| **ET Research** | Financial research engine with source verification, confidence scoring, fact-checking against curated knowledge base | Query |
| **Human Handoff** | Advisor escalation — detects complexity triggers, prepares context summary for human SEBI-registered RIA | Profile + history |
| **Family Wealth** | Consolidated multi-member family dashboard — linked portfolios, combined net worth, per-member analysis | Family links |
| **Life Event Advisor** | Windfall/bonus/inheritance allocation — prioritized deployment across emergency fund, goals, tax optimization, investments based on urgency | Life event + profile |
| **Expense Analytics** | Spending categorization, optimization suggestions, and spending score analysis | Profile + expenses |

### Support Agents

| Agent | Purpose |
|-------|---------|
| **RAG Agent** | Retrieval-augmented generation over 26 curated Indian financial documents in ChromaDB |
| **General Chat** | Fallback conversational agent for queries that don't match any specialist |
| **Onboarding** | Multi-step profile extraction (age, income, city, expenses, risk tolerance, language) from natural conversation |
### Compliance & Infrastructure

| Feature | Purpose |
|---------|--------|
| **SEBI Compliance Logger** | Every AI recommendation logged with agent name, intent, user ID, and timestamp for regulatory audit |
| **APScheduler Jobs** | 3 scheduled jobs — daily nudges (9 AM), periodic nudges (every 6h), pre-market briefing (9:15 AM) |
---

## Database Schema

Two separate PostgreSQL databases:

### creda_api (FastAPI — Alembic migrations)

```
┌──────────────┐     ┌───────────────────┐     ┌─────────────────┐
│    users      │     │   user_profiles    │     │   portfolios     │
├──────────────┤     ├───────────────────┤     ├─────────────────┤
│ id (PK)      │◄────│ user_id (FK)      │     │ id (PK)         │
│ email        │     │ name, age, city    │     │ user_id (FK) ───┼──► users
│ password_hash│     │ income, expenses   │     │ total_invested   │
│ name         │     │ risk_tolerance     │     │ current_value    │
│ is_active    │     │ language           │     │ xirr             │
│ created_at   │     │ insurance, loans   │     │ last_xray_at     │
│ updated_at   │     │ 35+ fields...      │     └─────────────────┘
└──────────────┘     └───────────────────┘              │
       │                                                 │
       │              ┌─────────────────────┐    ┌──────▼──────────┐
       │              │ conversation_messages│    │ portfolio_funds  │
       │              ├─────────────────────┤    ├─────────────────┤
       ├──────────────│ user_id (FK)        │    │ portfolio_id(FK)│
       │              │ session_id          │    │ fund_name       │
       │              │ role (user/assistant)│    │ folio_number    │
       │              │ content             │    │ units, nav       │
       │              │ intent              │    │ category        │
       │              │ language            │    │ expense_ratio   │
       │              │ created_at          │    │ overlap_score   │
       │              └─────────────────────┘    └─────────────────┘
       │
       │     ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐
       ├────▶│   nudges      │   │  goal_plans   │   │ whatsapp_sessions│
       │     ├──────────────┤   ├──────────────┤   ├─────────────────┤
       ├────▶│ user_id (FK) │   │ user_id (FK) │   │ phone_number     │
       │     │ nudge_type   │   │ goal_name    │   │ user_id (FK)     │
       └────▶│ title, body  │   │ target_amount│   │ language          │
             │ channel      │   │ monthly_sip  │   │ last_message_at   │
             │ is_read      │   │ deadline     │   └─────────────────┘
             │ sent_at      │   │ probability  │
             └──────────────┘   └──────────────┘

┌──────────────┐
│ life_events   │
├──────────────┤
│ user_id (FK) │
│ event_type    │
│ description   │
│ occurred_at   │
└──────────────┘

┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
│   budgets     │   │   expenses    │   │   advice_logs     │
├──────────────┤   ├──────────────┤   ├──────────────────┤
│ user_id (FK) │   │ user_id (FK) │   │ user_id (FK)      │
│ category     │   │ category     │   │ agent, intent      │
│ planned_amount│   │ amount       │   │ query, response    │
│ actual_amount│   │ description  │   │ suitability        │
│ month, year  │   │ date         │   │ created_at         │
└──────────────┘   │ payment_method│   └──────────────────┘
                   │ is_recurring │
                   └──────────────┘   ┌──────────────────┐
                                      │   activity_logs    │
┌──────────────────┐                  ├──────────────────┤
│  family_links     │                  │ user_id (FK)      │
├──────────────────┤                  │ action, detail     │
│ user_id (FK)      │                  │ ip, user_agent     │
│ linked_user_id(FK)│                  │ created_at         │
│ relationship      │                  └──────────────────┘
│ status            │
│ created_at        │                  ┌──────────────────┐
└──────────────────┘                  │email_verifications │
                                      ├──────────────────┤
                                      │ user_id (FK)      │
                                      │ token, verified    │
                                      │ expires_at         │
                                      └──────────────────┘
```

### creda_django (Django — Django ORM migrations)

```
Standard Django tables: auth_user, django_session, django_admin_log, etc.
Custom: accounts_user (extends AbstractUser with language field)
```

---

## API Endpoints

### Authentication (`/api/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/token` | Login → JWT token (rate limited: 5/min) |
| POST | `/api/auth/register` | Register new user (rate limited: 3/min) |

### Chat (`/api/chat`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/` | Send message → classified → agent → response |
| POST | `/api/chat/stream` | SSE stream for real-time responses |

### Voice (`/api/voice`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/voice/transcribe` | Audio → text (STT) |
| POST | `/api/voice/speak` | Text → audio (TTS) |
| POST | `/api/voice/pipeline` | Audio in → text + agent → audio out |

### Portfolio (`/api/portfolio`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/portfolio/upload` | Upload CAMS PDF statement |
| POST | `/api/portfolio/xray` | Run X-ray analysis on portfolio |
| POST | `/api/portfolio/refresh-navs` | Refresh NAVs for all holdings |
| GET | `/api/portfolio/summary` | Get portfolio summary |

### Agents (`/api/agents`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agents/fire-planner` | FIRE analysis |
| POST | `/api/agents/tax-wizard` | Tax regime comparison |
| POST | `/api/agents/money-health` | Financial health score |
| POST | `/api/agents/stress-test` | Monte Carlo stress test |
| POST | `/api/agents/budget-coach` | Budget 50/30/20 analysis |
| POST | `/api/agents/goal-planner` | Goal-based SIP planning |
| POST | `/api/agents/couples-finance` | Joint financial analysis |
| POST | `/api/agents/market-pulse` | Real-time market data |
| POST | `/api/agents/tax-copilot` | Live tax optimization |
| POST | `/api/agents/money-personality` | Behavioral analysis |
| POST | `/api/agents/goal-simulator` | Monte Carlo goal simulation |
| POST | `/api/agents/social-proof` | Peer benchmarking |
| POST | `/api/agents/et-research` | Financial research |
| POST | `/api/agents/human-handoff` | Advisor escalation |
| POST | `/api/agents/family-wealth` | Family wealth analysis |
| POST | `/api/agents/life-event-advisor` | Life event / windfall allocation |
| POST | `/api/agents/expense-analytics` | Expense analysis + optimization |

### Profile (`/api/profile`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/profile/upsert` | Create or update user profile |
| GET | `/api/profile/{user_id}` | Get user profile |
| GET | `/api/profile/{user_id}/is-onboarded` | Check onboarding status |

### Nudges (`/api/nudges`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/nudges/pending` | Get unread nudges |
| POST | `/api/nudges/generate` | Dynamically generate nudges from user profile |
| POST | `/api/nudges/{id}/read` | Mark nudge as read |
| POST | `/api/nudges/mark-all-read` | Mark all as read |

### WhatsApp (`/api/whatsapp`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/whatsapp/webhook` | Twilio incoming message webhook |

### Compliance (`/api/compliance`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/compliance/report` | Generate SEBI compliance report |
| GET | `/api/compliance/ai-disclosure` | AI disclosure information |

### Family (`/api/family`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/family/link` | Create family member link |
| POST | `/api/family/accept/{link_id}` | Accept family link invitation |
| GET | `/api/family/members` | List all family members |
| DELETE | `/api/family/unlink/{link_id}` | Remove family member link |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Full health check (Postgres, Redis, ChromaDB, TTS) |

### Budget & Expenses (`/api/budget`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/budget/expense` | Create expense record |
| GET | `/api/budget/summary` | Budget vs actual summary |

### Export (`/api/export`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export/{type}/csv` | Export data as CSV (portfolio, expenses, goals) |
| GET | `/api/export/{type}/pdf` | Export data as PDF report |

### Admin (`/api/admin`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Platform-wide usage statistics |
| GET | `/api/admin/users` | User listing with activity metrics |

---

## Frontend Pages

| URL | Page | Description |
|-----|------|-------------|
| `/` | Landing | Public marketing page with features, security, CTAs |
| `/dashboard/` | Dashboard | Overview metrics, quick actions, intelligence modules |
| `/chat/` | AI Chat | Conversational interface with suggestion cards |
| `/portfolio/` | Portfolio | CAMS PDF upload + fund-level X-ray table |
| `/health/` | Money Health | 0-100 score with 6 dimension bars |
| `/fire/` | FIRE Planner | FIRE number, savings rate, years to independence |
| `/tax/` | Tax Wizard | Old vs New regime comparison with deductions |
| `/budget/` | Budget Coach | 50/30/20 rule analysis with progress bars |
| `/goals/` | Goal Planner | Goal cards with SIP amounts and progress |
| `/stress-test/` | Stress Test | Scenario selection + P10/P50/P90 outcomes |
| `/settings/` | Settings | Profile editing form |
| `/onboarding/` | Onboarding | 6-step profile wizard |
| `/notifications/` | Notifications | Proactive nudges feed |
| `/couples/` | Couples Finance | Joint financial analysis |
| `/sip-calculator/` | SIP Calculator | Projections with growth scenarios |
| `/market-pulse/` | Market Pulse | Live indices, news, portfolio impact |
| `/tax-copilot/` | Tax Copilot | Deduction tracker + harvesting opportunities |
| `/personality/` | Money Personality | Archetype + traits + blind spots |
| `/goal-simulator/` | Goal Simulator | Monte Carlo with year-by-year table |
| `/social-proof/` | Social Proof | Peer benchmarks + percentile rankings |
| `/research/` | Research | Search with confidence scoring + sources |
| `/voice/` | Voice | Full voice interface with recording + playback |
| `/advisor/` | Advisor | Human handoff with escalation triggers |
| `/expenses/` | Expense Analytics | Spending breakdown + optimization |
| `/life-events/` | Life Events | Bonus/windfall allocation advisor |
| `/compliance/` | Compliance | SEBI compliance audit log and AI disclosure |
| `/family/` | Family | Multi-member family wealth dashboard |
| `/admin/` | Admin | User management + system stats |
| `/report-card/` | Report Card | Monthly financial summary + trends |

**UX Features (across all pages):**

| Feature | Description |
|---------|-------------|
| **Page Explainers** | Collapsible "What is this?" sections on 7 major pages (Health, FIRE, Budget, Expenses, Couples, Tax, Stress Test) with plain-English explanations for new users |
| **Markdown Stripping** | Custom `creda_filters` templatetag strips `**bold**` and `*italic*` LLM artifacts from all agent responses |
| **Indian Number Formatting** | Numbers displayed with Indian comma system (e.g., ₹7,20,00,000 instead of ₹72,000,000) |
| **Language Switcher** | Top navigation bar dropdown for instant language switching (in addition to sidebar toggle) |
| **Partner Invite** | Couples Finance page allows inviting partner by email when no spouse is linked |
| **HTMX Partials** | Health Score and Market Pulse use async HTMX partial loading with skeleton states |

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **Docker Desktop** (for Postgres, Redis, ChromaDB, TTS engines)
- **Make** (GNU Make — install via `choco install make` on Windows)
- **Groq API Key** (free at [console.groq.com](https://console.groq.com))

### Quick Start

```bash
cd python/

# 1. One-time setup: creates venv, installs deps, copies .env, starts Docker, runs migrations
make init

# 2. Edit .env — add your GROQ_API_KEY
notepad .env

# 3. Start everything (Docker + Backend + Frontend in separate windows)
make all

# 4. Open in browser
# http://localhost:8000
```

### Demo Accounts

Two pre-built demo accounts come with the platform for the **"Arjun’s Story"** hackathon demo scenario. Seed them with:

```bash
make seed
```

| Account | Email | Password | Profile |
|---------|-------|----------|--------|
| **Arjun Mehta** | `arjun@demo.creda.in` | `demo1234` | 29, Salaried IT (Bengaluru), ₹1.8L/mo income, Moderate risk, 6 mutual funds (₹8.3L portfolio), 4 goals, 2 life events, 25 real expenses, 10 budget categories |
| **Priya Sharma** | `priya@demo.creda.in` | `demo1234` | 27, Product Manager (Bengaluru), ₹1.4L/mo income, Moderate risk, 2 mutual funds (₹3.2L portfolio), 2 goals |

- Arjun & Priya are pre-linked as a **spouse pair** for Couples Finance
- Arjun has **deliberate portfolio problems**: 3 large-cap overlap, Nifty 50 underperformance, no debt allocation
- Arjun has **25 realistic seeded expenses** (rent, groceries, transport, dining, utilities, subscriptions) + **10 monthly budgets** with planned vs actual amounts powering Expense Analytics
- Arjun’s Money Health Score starts at **42/100 (RED)** — drives the demo narrative
- Dynamic nudges are generated on dashboard load (no pre-seeded conversations)
- See full demo scenario in [`demo/README.md`](demo/README.md)

---

### Manual Setup

If you prefer not to use the Makefile:

```powershell
cd python/

# 1. Create virtual environment
python -m venv ../.venv
../.venv/Scripts/Activate.ps1

# 2. Install dependencies
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt

# 3. Setup environment
Copy-Item .env.example .env
# Edit .env with your GROQ_API_KEY

# 4. Start Docker services
docker compose up -d postgres redis chroma kokoro-tts piper-tts

# 5. Wait for Postgres health check, then run migrations
Start-Sleep -Seconds 15
cd frontend; python manage.py migrate; cd ..
cd backend; python -m alembic upgrade head; cd ..

# 6. Start FastAPI backend (new terminal)
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# 7. Start Django frontend (new terminal)
cd frontend
python manage.py runserver 8000
```

### Docker Compose (Production)

To run everything in containers (including backend + frontend):

```bash
cd python/

# Copy and edit environment
cp .env.example .env
# Edit .env

# Start all 7 services
docker compose up --build -d

# Run migrations inside containers
docker exec creda_backend python -m alembic upgrade head
docker exec creda_frontend python manage.py migrate

# Create admin user
docker exec -it creda_frontend python manage.py createsuperuser

# Open http://localhost:8000
```

**Docker services:**

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `backend` | Custom (Python 3.12) | 8001 | FastAPI + 22 agents + scheduler |
| `frontend` | Custom (Python 3.12) | 8000 | Django + SSR templates |
| `postgres` | postgres:15 | 8010 | Dual database (creda_api + creda_django) |
| `redis` | redis:7-alpine | 8020 | Session cache + conversation store |
| `chroma` | chromadb/chroma | 8030 | RAG vector database |
| `kokoro-tts` | kokoro-fastapi-cpu | 8880 | Primary TTS engine |
| `piper-tts` | wyoming-piper | 8890 | Fallback TTS engine |

---

## Makefile Commands

Run all commands from the `python/` directory:

| Command | Description |
|---------|-------------|
| `make init` | **One-time setup** — venv + deps + env + download model + docker + migrations |
| `make all` | **Start everything** — Docker + Backend + Frontend |
| `make docker` | Start Docker infrastructure only |
| `make download-model` | Download all-MiniLM-L6-v2 to local `models/` for offline embedding |
| `make backend` | Start FastAPI (foreground, port 8001) |
| `make backend-bg` | Start FastAPI (new window) |
| `make frontend` | Start Django (foreground, port 8000) |
| `make frontend-bg` | Start Django (new window) |
| `make stop` | Stop all services |
| `make restart-backend` | Restart backend |
| `make restart-frontend` | Restart frontend |
| `make migrate` | Run Django + Alembic migrations |
| `make seed` | Seed demo accounts (Arjun & Priya) with portfolios, goals, nudges, family link |
| `make superuser` | Create Django admin superuser |
| `make db-shell` | Open psql shell |
| `make test` | Health check both services |
| `make status` | Show status of all ports/containers |
| `make logs` | Tail Docker logs |
| `make clean` | Remove `__pycache__` |
| `make nuke` | **Wipe everything** — stop + delete volumes + rebuild |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | Async PostgreSQL URL for FastAPI |
| `DJANGO_DATABASE_URL` | Yes | — | PostgreSQL URL for Django |
| `REDIS_URL` | Yes | `redis://localhost:8020/0` | Redis connection |
| `JWT_SECRET` | Yes | `change-me...` | JWT signing secret |
| `DJANGO_SECRET_KEY` | Yes | `change-me...` | Django secret key |
| `GROQ_API_KEY` | **Yes** | — | Groq LLM API key |
| `KOKORO_TTS_URL` | No | `http://localhost:8880` | Kokoro TTS endpoint |
| `PIPER_TTS_URL` | No | `http://localhost:8890` | Piper TTS endpoint |
| `STT_ENGINE` | No | `faster-whisper` | STT engine choice |
| `CHROMA_HOST` | No | `localhost` | ChromaDB host |
| `CHROMA_PORT` | No | `8030` | ChromaDB port |
| `TWILIO_ACCOUNT_SID` | No | — | Twilio SID (for WhatsApp) |
| `TWILIO_AUTH_TOKEN` | No | — | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | No | — | Twilio WhatsApp number |
| `DJANGO_DEBUG` | No | `false` | Django debug mode |
| `DJANGO_PORT` | No | `8000` | Django port |
| `FASTAPI_PORT` | No | `8001` | FastAPI port |

---

## Design System

The frontend uses a custom glassmorphism design system built on Tailwind CSS:

| Element | Style |
|---------|-------|
| **Cards** | `glass` class — `backdrop-blur-xl bg-white/70 dark:bg-slate-800/50`, `rounded-[2rem]`, `border border-slate-200/50` |
| **Headings** | `font-black italic` — bold italic for emphasis |
| **Labels** | `text-[10px] font-bold uppercase tracking-[0.15em]` — small caps |
| **Inputs** | Glass background, `focus:border-blue-500`, `rounded-xl` |
| **Primary Color** | `blue-600` — buttons, active states, accents |
| **Sidebar** | White/dark collapsible, 24 SVG-icon nav links, section groups |
| **Dark Mode** | Alpine.js toggle with `localStorage` persistence, `dark:` variants |
| **Animations** | `animate-fade-in`, `animate-slide-up`, `animate-float` |
| **Icons** | SVG (no emoji) — professional, consistent sizing |

---

## Intent Classification Engine

CREDA uses a production-grade **4-tier cascading classifier** inspired by how ChatGPT and Claude route queries internally. Each tier is faster but less powerful than the next — the first confident match wins, saving ~95% of LLM API calls.

| Tier | Name | Latency | How It Works | LLM? |
|------|------|---------|-------------|------|
| **1** | Follow-up Detection | 0ms | Regex detects "yes", "tell me more", "हाँ", "ஆம்" → reuses last agent from Redis | No |
| **2** | Weighted Keyword Scoring | 0ms | 70+ regex patterns × 22 intents, each with specificity weight (1.0–3.0). Disambiguates multi-keyword matches via score gap analysis. Supports 8 Indian languages + Hinglish | No |
| **3** | Embedding Similarity | ~10ms | sentence-transformers/all-MiniLM-L6-v2 (87MB, runs on CPU, fully offline). 22 pre-computed intent centroids from curated trigger phrases. Cosine similarity ≥ 0.78 → route directly | ML (local) |
| **4** | LLM Classifier | 1–2s | Groq llama-3.1-8b with hints from Tiers 2–3 to help disambiguate. Only reached for ~5% of queries | LLM |

**Model Management:**
- The MiniLM model is downloaded once during `make init` (or `make download-model`) and stored locally at `models/all-MiniLM-L6-v2/`
- The `models/` directory is gitignored — no large files in the repo
- On first use, if the local model doesn't exist, it auto-downloads from HuggingFace and saves locally
- Subsequent starts are fully offline — zero network calls for Tier 3

**Files:**

| File | Role |
|------|------|
| `services/intent_engine.py` | Orchestrator — runs all 4 tiers in cascade, returns `IntentResult` with confidence, tier, and debug scores |
| `services/intent_classifier.py` | Tier 2 — weighted keyword scoring with multilingual regex patterns |
| `services/intent_embeddings.py` | Tier 3 — MiniLM model loading, centroid computation, cosine similarity matching |
| `agents/intent_router.py` | Tier 4 — LLM classifier with hint injection from lower tiers |

---

## Knowledge Base

The RAG agent is backed by **26 curated documents** in `backend/knowledge/documents.yaml`, loaded into ChromaDB on startup:

| Category | Documents |
|----------|-----------|
| **Government Schemes** | PMJJBY, PMSBY, Sukanya Samriddhi, NPS, PPF, SGB, APY, SCSS |
| **Tax Rules** | Section 80C, LTCG/STCG, HRA exemption, advanced tax planning |
| **Investment** | Asset allocation, SIP guide, index funds |
| **Insurance** | Term life insurance, health insurance |
| **Behavioral** | Money personality archetypes, biases |
| **Planning** | Goal-based planning, FIRE targets, Monte Carlo |
| **Benchmarks** | Indian household financial benchmarks by age group |
| **Research** | Financial fact-checking methodology |
| **Advisory** | Human handoff escalation criteria |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run health checks: `make test`
5. Commit: `git commit -m "feat: your feature"`
6. Push and create a Pull Request

---

<p align="center">
  Built with ❤️ for every Indian household
</p>
