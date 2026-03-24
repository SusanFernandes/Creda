# CREDA

> AI-powered multilingual financial advisory platform for India.

CREDA delivers personalised financial coaching — portfolio X-Ray, retirement planning, tax optimisation, budget coaching, and regulatory Q&A — through voice and text in **11 Indian languages**.

Two products ship from the same codebase:

| Product | Target | Key Feature |
|---------|--------|-------------|
| **CREDA** | Mass-market (mobile app, voice) | Multilingual financial coach for all Indians |
| **ET PS9** | Economic Times readers (web) | MF Portfolio X-Ray + Life Event Stress Tester |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  API Gateway  (Port 8080)                 │
│                        app.py                             │
│  • Intelligent routing   • Health checks   • CORS        │
└────────────┬──────────────────────────┬──────────────────┘
             │                          │
  ┌──────────▼──────────┐   ┌──────────▼───────────────┐
  │  Multilingual Svc    │   │  Finance Service          │
  │  Port 8000           │   │  Port 8001                │
  │  fastapi1_multi…py   │   │  fastapi2_finance.py      │
  │                      │   │                           │
  │  • ASR (IndicConf.)  │   │  • LangGraph agents       │
  │  • LLM (Groq)        │   │  • SQLite persistence     │
  │  • TTS (Parler-TTS)  │   │  • RAG (ChromaDB)         │
  │  • Translation       │   │  • CAMS PDF X-Ray         │
  │    (IndicTrans2)     │   │  • Stress testing         │
  └──────────────────────┘   │  • FIRE planner           │
                             │  • Tax wizard             │
                             │  • Money health score     │
                             └───────────────────────────┘

  ┌────────────────────────────────────────────────────────┐
  │                       Clients                           │
  │  Creda_App (Expo/RN)  │  Creda_Website (React/Vite)   │
  │  Twilio Voice Agent   │  Any HTTP client               │
  └────────────────────────────────────────────────────────┘
```

### Request Flow

1. **Client** sends request to Gateway (`:8080`)
2. Gateway routes to the correct backend service
3. **Voice flow**: Audio → ASR → LLM → Finance Service → LLM → TTS → Audio
4. **Text/API flow**: JSON → Finance Service (LangGraph) → JSON response
5. Finance Service uses intent detection to route to specialist agents:
   - `portfolio_xray` → CAMS PDF parser + XIRR + overlap + rebalancing
   - `stress_test` → Monte Carlo life-event simulation
   - `fire_planner` → FIRE number + SIP roadmap + insurance gap
   - `tax_wizard` → Old vs New regime comparison + missed deductions
   - `money_health_score` → 6-dimension financial health (0–100)
   - `rag_query` → ChromaDB knowledge base (RBI/SEBI/IRDAI regulations)

---

## Folder Structure

```
Creda/
├── Creda_Fastapi/      # Backend — Gateway + Multilingual + Finance services
├── Creda_App/          # Mobile app — Expo / React Native
├── Creda_Website/      # Web app — React + Vite + TailwindCSS
└── Creda_Rag/          # Legacy RAG service (Twilio + Flask, Port 5000)
```

Each folder has its own README with setup and run instructions.

---

## Quick Start

### 1. Clone & enter

```bash
git clone <repo-url>
cd Creda
```

### 2. Backend (Creda_Fastapi)

```bash
cd Creda_Fastapi
python -m venv .venv        # or use the project-level venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\Activate    # Windows

# Install with uv (recommended)
uv pip install -e ".[multilingual]"

# Or with pip
pip install -e ".[multilingual]"

# Copy .env.example → .env and fill in keys
cp .env.example .env

# Start all services
python app.py               # Gateway on :8080
python fastapi1_multilingual.py  # Multilingual on :8000 (separate terminal)
python fastapi2_finance.py       # Finance on :8001 (separate terminal)
```

### 3. Website (Creda_Website)

```bash
cd Creda_Website
bun install     # or npm install
bun dev         # Vite dev server on :5173
```

### 4. Mobile App (Creda_App)

```bash
cd Creda_App
npx expo install
npx expo start
```

---

## API Overview

All clients hit the Gateway on **Port 8080**. Key endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Main conversational AI (routes to LangGraph) |
| `/voice/command` | POST | **Push-to-talk**: audio → ASR → Groq function-calling → structured intent (navigation / action / answer) |
| `/process_voice` | POST | Full voice pipeline: audio → ASR → LLM → TTS → audio stream |
| `/tts_only` | POST | Text → Indic Parler-TTS audio (multilingual confirmations) |
| `/twilio/voice` | POST | Incoming Twilio call handler (persistent sessions) |
| `/twilio/process_speech` | POST | Twilio Gather continuation (multi-turn voice) |
| `/portfolio/xray` | POST | CAMS PDF upload → full portfolio analysis |
| `/portfolio/stress-test` | POST | Life event simulation |
| `/fire-planner` | POST | FIRE / retirement roadmap |
| `/money-health-score` | POST | 6-dimension financial health score |
| `/tax-wizard` | POST | Old vs New tax regime comparison |
| `/sip-calculator` | POST | SIP growth projection |
| `/profile/upsert` | POST | Create/update user profile |
| `/profile/{user_id}` | GET | Retrieve user profile |
| `/health` | GET | Service health status |
| `/docs` | GET | Swagger UI (auto-generated) |

Full API docs available at `http://localhost:8080/docs` when running.

---

## Use Cases

- **Retail Investors**: Personalised investment strategies — "Should I invest in ELSS for tax savings?"
- **Budget Planners**: Adaptive spending insights — "Where is my money going each month?"
- **Portfolio Holders**: Upload CAMS PDF, get true XIRR, overlap, benchmark comparison, rebalancing plan
- **Tax Filers**: Compare old vs new regime with your specific numbers, find missed deductions
- **Couples**: Joint optimisation — HRA claims, NPS matching, SIP splits across both incomes
- **Voice Callers**: Call CREDA phone number (Twilio) — multi-turn conversations, persistent session storage, advice via voice
- **Non-Tech Users**: Elders, low-digital-literacy users can phone for financial guidance

---

## Performance

| Operation | Target |
|-----------|--------|
| Voice pipeline (ASR → LLM → TTS) | < 3s for 10s audio |
| Twilio voice call (text → TwiML) | < 2s (Polly.Aditi) |
| LangGraph chat (intent + agent + synthesis) | < 2s |
| CAMS PDF parse + XIRR | < 1s |
| RAG query | < 0.5s |
| SIP calculator (pure math) | < 50ms |

---

## Security & Compliance

- **No persistent PII** — session data can be purged; user profiles stored only when explicitly created
- **Regulatory RAG** — all financial advice is backed by 52 authoritative documents from RBI, SEBI, IRDAI, PFRDA, EPFO
- **Disclaimer built-in** — every LLM response notes this is informational, not personalised advice
- **CORS** — configurable per environment
- **Future** — Account Aggregator (AA) framework planned for consent-based real bank/MF data access

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Gateway** | FastAPI, httpx (async routing) |
| **LLM** | Groq (llama-3.3-70b, free tier) |
| **Agent Orchestration** | LangGraph (multi-agent state graph) |
| **ASR** | AI4Bharat IndicConformer-600M |
| **TTS** | Indic Parler-TTS |
| **Translation** | AI4Bharat IndicTrans2 |
| **RAG** | ChromaDB + SentenceTransformers |
| **Database** | SQLite via SQLModel |
| **Financial Math** | pyxirr (XIRR), casparser (CAMS PDF) |
| **Market Data** | yfinance |
| **Web Frontend** | React + Vite + TailwindCSS |
| **Mobile** | Expo + React Native + NativeWind |

---

## Environment Variables

Create `.env` in `Creda_Fastapi/`:

```env
GROQ_API_KEY=your_groq_key          # https://console.groq.com (free)
HF_TOKEN=your_hf_token              # https://huggingface.co/settings/tokens
FASTAPI1_URL=http://localhost:8000
FASTAPI2_URL=http://localhost:8001
GATEWAY_PORT=8080
DATABASE_URL=sqlite:///./creda.db
LOG_LEVEL=INFO
```

---

## Languages Supported

Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Urdu, English.

---

## Key Innovations

- **LangGraph Multi-Agent**: 6 specialist financial agents (portfolio, tax, FIRE, health, stress, RAG) orchestrated via a compiled state graph with conditional routing
- **True XIRR**: Rust-powered `pyxirr` computes actual internal rate of return from CAMS transaction history — not simplified CAGR
- **Benchmark Comparison**: Live yfinance data compares each fund against Nifty 50, Nifty Midcap/Smallcap indices — shows per-fund alpha
- **52-Document RAG**: ChromaDB with SEBI/RBI/IRDAI/PFRDA knowledge — regulations, schemes, tax rules, seasonal advice, regional preferences
- **Monte Carlo Stress Testing**: 500-simulation engine for life events (market crash, baby, marriage, job change) with P10/P50/P90 outcomes
- **Voice-First Multilingual**: AI4Bharat IndicConformer + IndicTrans2 + Parler-TTS — end-to-end voice in 11 Indian languages
- **Indian Tax Engine**: Hard-coded FY2024-25 slab math (not LLM-generated) for Old and New regime — deterministic, accurate

---

## Acknowledgements

- **AI4Bharat** — IndicConformer, IndicTrans2, Parler-TTS models for Indian language AI
- **Groq** — Free-tier llama-3.3-70b inference powering all LLM calls
- **ChromaDB** — Persistent vector database for financial knowledge
- **SEBI, RBI, IRDAI, PFRDA, EPFO** — Regulatory source material for the RAG knowledge base

---

## License

MIT
