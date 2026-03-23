# Creda Backend — FastAPI Services

Backend for the CREDA platform. Three FastAPI services behind an API gateway:

| Service | File | Port | Purpose |
|---------|------|------|---------|
| **Gateway** | `app.py` | 8080 | Routes requests to downstream services |
| **Multilingual** | `fastapi1_multilingual.py` | 8000 | ASR, TTS, translation, voice pipeline |
| **Finance** | `fastapi2_finance.py` | 8001 | LangGraph agents, portfolio analysis, planning |

---

## Prerequisites

- **Python 3.12+** (tested with 3.12.12)
- **uv** (recommended) or pip
- Groq API key (free at https://console.groq.com)
- HuggingFace token (for ASR/TTS models)

---

## Setup

### 1. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\Activate      # Windows
```

### 2. Install dependencies

```bash
# Core (Finance + Gateway) — fast, no heavy ML models
uv pip install -e .

# Full (includes Multilingual ASR/TTS/Translation — downloads ~8GB of models)
uv pip install -e ".[multilingual]"

# Dev tools (pytest, ruff)
uv pip install -e ".[dev]"
```

Or with the lock file for exact reproducibility:

```bash
uv pip install -r requirements-lock.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=gsk_your_key_here
HF_TOKEN=hf_your_token_here
FASTAPI1_URL=http://localhost:8000
FASTAPI2_URL=http://localhost:8001
GATEWAY_PORT=8080
DATABASE_URL=sqlite:///./creda.db
CHROMA_DB_PATH=./chroma_financial_db
LOG_LEVEL=INFO
```

### 4. Start services

Start each in a separate terminal:

```bash
# Terminal 1 — Gateway
python app.py

# Terminal 2 — Finance Service
python fastapi2_finance.py

# Terminal 3 — Multilingual Service (optional, needs .[multilingual])
python fastapi1_multilingual.py
```

Gateway auto-detects which downstream services are available. If Multilingual isn't running, voice features are unavailable but all finance APIs still work.

---

## Project Structure

```
Creda_Fastapi/
├── app.py                       # API Gateway (port 8080)
├── fastapi1_multilingual.py     # Multilingual service (port 8000)
├── fastapi2_finance.py          # Finance service (port 8001)
├── models.py                    # SQLModel database tables
├── agents/                      # LangGraph agent modules
│   ├── state.py                 # Shared FinancialState TypedDict
│   ├── intent_router.py         # 12-intent LLM classifier
│   ├── portfolio_xray_agent.py  # CAMS PDF → XIRR + overlap + rebalancing
│   ├── stress_test_agent.py     # Monte Carlo life event simulation
│   ├── fire_planner_agent.py    # FIRE number + SIP roadmap
│   ├── tax_wizard_agent.py      # Old vs New regime FY2024-25
│   ├── money_health_agent.py    # 6-dimension health score
│   ├── rag_agent.py             # ChromaDB knowledge base (52 docs)
│   └── graph.py                 # StateGraph compilation & routing
├── pyproject.toml               # Dependency management
├── requirements-lock.txt        # Frozen (185 packages)
├── docker-compose.yml           # Multi-service Docker setup
├── Dockerfile                   # Multilingual service container
├── Dockerfile.finance           # Finance service container
└── .env.example                 # Environment template
```

---

## Finance Service — API Reference (Port 8001)

### Core

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check + RAG + DB status |

### Chat (LangGraph)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Conversational AI — routes to specialist agent via intent detection |
| `/twilio/voice` | POST | **NEW:** Incoming Twilio voice call handler — returns TwiML (Say + Gather) |
| `/twilio/process_speech` | POST | **NEW:** Twilio Gather continuation — multi-turn voice conversation |
| `/twilio/brain` | POST | *(Legacy)* Old Twilio endpoint — returns JSON text |

### Portfolio

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portfolio/xray` | POST | Upload CAMS/KFintech PDF → XIRR, overlap, expense drag, benchmark comparison (yfinance), rebalancing |
| `/portfolio/stress-test` | POST | Simulate life events (market crash, baby, home purchase, etc.) |
| `/portfolio/history/{user_id}` | GET | Historical portfolio snapshots |

### Planning

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fire-planner` | POST | FIRE number, year-by-year roadmap, insurance gaps, tax savings |
| `/money-health-score` | POST | 6-dimension score: emergency, insurance, diversification, debt, tax, retirement |
| `/tax-wizard` | POST | Old vs New regime comparison, missed deductions, recoverable tax |
| `/sip-calculator` | POST | SIP growth projection with step-up (pure math, no LLM) |
| `/couples-planner` | POST | Joint plan — loads both partners' profiles, optimises HRA/NPS/SIP splits |

### Profile

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/profile/upsert` | POST | Create or update user financial profile |
| `/profile/{user_id}` | GET | Retrieve stored profile |

### Backward Compatible

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rag_query` | POST | Direct RAG search |
| `/process_request` | POST | Generic request processing |
| `/get_portfolio_allocation` | GET | Default allocation |
| `/knowledge_base_stats` | GET | ChromaDB collection stats |
| `/supported_features` | GET | Feature list with descriptions |

---

## Multilingual Service — API Reference (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/process_voice` | POST | Full pipeline: audio → ASR → LLM → TTS → audio |
| `/process_text` | POST | Text → LLM → translated response |
| `/transcribe` | POST | Audio → text (ASR only) |
| `/translate` | POST | Text translation between Indian languages |
| `/tts/synthesize` | POST | Text → audio (TTS only) |
| `/supported_languages` | GET | List of supported languages |

---

## LangGraph Agent Architecture

```
User Message
     │
     ▼
┌──────────────┐
│ Intent Router │  ← LLM classifies into 1 of 12 intents
└──────┬───────┘
       │
       ▼ (conditional edge)
┌──────────────────────────────────────────┐
│  portfolio_xray  │  stress_test          │
│  fire_planner    │  money_health_score   │
│  tax_wizard      │  rag_query            │
│  sip_calculator  │  budget_coach         │
│  insurance_check │  goal_planner         │
│  couples_planner │  general_chat         │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│ Response Synth.  │  ← Merges agent output into ≤150-word voice-friendly answer
└──────────────────┘
       │
       ▼
   Final Response
```

---

## Database (SQLite)

Four tables managed by SQLModel:

| Table | Purpose |
|-------|---------|
| `UserProfile` | Financial profile — income, expenses, 80C/80CCD/NPS deductions, dependents |
| `PortfolioSnapshot` | XIRR results, fund holdings JSON, parsed from CAMS PDFs |
| `ConversationMessage` | Chat history per session (role + content + intent) — **NEW:** `call_sid` (Twilio), `content_type` (text/voice_metadata) |
| `LifeEvent` | Stress test results and life event records |

DB file: `creda.db` (auto-created on first run).

### Twilio Voice — Database Schema

When a user calls your Twilio number, all interactions are stored:

```sql
SELECT * FROM conversation_messages 
WHERE call_sid = 'CA_...' 
ORDER BY timestamp;
```

Columns:
- `session_id`: set to `call_sid`
- `user_id`: `voice_{call_sid}`
- `call_sid`: Twilio's unique call identifier
- `role`: "user" | "assistant" | "system"
- `content`: Message text
- `content_type`: "text" (default) | "voice_metadata"
- `timestamp`: When recorded

---

## Twilio Voice Integration

### Setup

1. **Get a Twilio phone number** at https://console.twilio.com
2. **Set webhook** in Twilio Console:
   ```
   Phone Number → Voice → Call Comes In
   Webhook URL: https://your-domain/twilio/voice
   HTTP Method: POST
   ```
3. **Verify endpoint** is accessible (use ngrok for local testing)

### Call Flow

```
User calls your number
         ↓
Twilio → POST /twilio/voice (CallSid, no speech_result)
         ↓
Finance Service → Returns TwiML: "Welcome to CREDA..." + Gather
         ↓
Twilio → Plays greeting, waits for speech
         ↓
User speaks
         ↓
Twilio → POST /twilio/process_speech (speech_result captured)
         ↓
Finance Service → Routes through LangGraph agents
         ↓
Database → Stores user message + AI response (indexed by call_sid)
         ↓
Returns TwiML: AI response + Gather for next turn
         ↓
User can speak again or say "goodbye" to hangup
```

### Features

- ✅ Multi-turn conversations (user asks multiple questions)
- ✅ Full session persistence (queryable by call_sid)
- ✅ Voice-optimized responses (truncated to 300 chars ~ 30s audio)
- ✅ Indian English voice (Polly.Aditi)
- ✅ Hangup detection ("bye", "goodbye", "exit")
- ✅ LangGraph agent routing (all 6 specialists available)
- ✅ Error handling + TwiML fallback

### Example Query

```bash
# Simulate incoming Twilio call
curl -X POST http://localhost:8080/twilio/voice \
  -d "call_sid=CA_TEST_12345" \
  -d "speech_result=Tell me about taxes"
```

### Audit Trail

```bash
sqlite3 creda.db << EOF
SELECT timestamp, role, content FROM conversation_messages 
WHERE call_sid LIKE 'CA%' 
ORDER BY timestamp;
EOF
```

---

## Testing

```bash
# Quick health check
curl http://localhost:8080/health

# Chat
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "What is my money health score?", "language": "en"}'

# SIP calculator (no LLM needed)
curl -X POST http://localhost:8001/sip-calculator \
  -H "Content-Type: application/json" \
  -d '{"monthly_amount": 10000, "expected_return": 12, "years": 15}'

# Run test suite
pytest test_gateway.py -v
```

---

## Docker

```bash
docker-compose up --build
```

Spins up all three services with the same port mapping.
