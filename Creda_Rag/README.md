# Creda_Rag — Legacy Voice Agent (Flask + Twilio)

> **Status: SUPERSEDED ✅**
> 
> Voice functionality now **fully integrated** into **Creda_Fastapi** Finance Service v2.0
> 
> This was the original prototype. The new integrated version provides multi-agent LangGraph orchestration, full portfolio analysis, 52-document RAG, SQLite persistence, and seamless gateway integration.

Original voice-based financial assistant using Flask, Twilio, and a basic RAG pipeline. This was the first prototype of CREDA's voice capability.

::: details Why the change?
**V1 (Creda_Rag):**
- ❌ Flask (limited scaling)
- ❌ In-memory sessions (lost on restart)
- ❌ Single LLM call (no agent routing)
- ❌ 4 SQLite collections for RAG

**V2 (Integrated):**
- ✅ FastAPI (async, production-ready)
- ✅ SQLite persistence with `call_sid` indexing
- ✅ LangGraph multi-agent (6 specialists)
- ✅ 52-document ChromaDB RAG
- ✅ Full portfolio analysis (XIRR, benchmarks, overlap)
- ✅ Planning agents (FIRE, tax, health, stress test)
- ✅ Gateway + multilingual service integration
:::

---

## What It Does

- Receives voice calls via **Twilio** webhook
- Converts speech to text
- Queries a **SQLite knowledge base** of Indian financial products and regulations
- Generates a response using **Groq LLM** (llama-3.3-70b)
- Sends the response back as voice via Twilio

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | Flask server — Twilio webhook handler + RAG query pipeline |
| `knowledge_setup.py` | Seeds the SQLite knowledge base with financial data |
| `twilio_setup.py` | Configures Twilio phone number webhooks |
| `test_groq.py` | Quick test for Groq API connectivity |

---

## Setup

### 1. Install dependencies

```bash
cd Creda_Rag
pip install flask groq twilio
```

### 2. Configure environment

Create `.env`:

```env
GROQ_API_KEY=your_groq_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
```

### 3. Seed knowledge base

```bash
python knowledge_setup.py
```

This creates `financial_data.db` with pre-loaded Indian financial knowledge.

### 4. Run

```bash
python app.py
# Starts Flask on port 5000
```

### 5. Expose for Twilio

Use ngrok or a public URL:

```bash
ngrok http 5000
```

Then configure the Twilio webhook URL to `https://your-ngrok-url/voice`.

---

## Migration to Finance Service v2.0

### Quick Start

```bash
cd Creda_Fastapi
python app.py                    # Terminal 1: Gateway on :8080
python fastapi2_finance.py       # Terminal 2: Finance on :8001
```

### Configure Twilio Webhook

In Twilio Console:
```
Phone Number → Voice → Call Comes In
Webhook URL: https://your-domain.com/twilio/voice
HTTP Method: POST
```

### Comparison

| Feature | Creda_Rag | Finance v2.0 |
|---------|-----------|--------------|
| **Framework** | Flask | FastAPI + async |
| **Scaling** | Single instance | Production-ready |
| **Persistence** | In-memory (lost on restart) | SQLite (indexed by call_sid) |
| **LLM Strategy** | Single Groq call | LangGraph multi-agent |
| **Knowledge Base** | 4 SQLite collections | 52-doc ChromaDB RAG |
| **Portfolio Analysis** | ❌ None | ✅ XIRR, overlap, benchmarks |
| **Planning** | ❌ Basic | ✅ FIRE, tax, health, stress test |
| **Voice Quality** | Basic | Full TwiML control (Say + Gather) |
| **Integration** | Standalone | Gateway + multilingual service |

### If you still need Creda_Rag

```bash
cd Creda_Fastapi
python fastapi2_finance.py   # Port 8001, /twilio/brain endpoint
```

The v2.0 `/twilio/brain` endpoint provides the same Twilio voice webhook functionality but with:
- LangGraph multi-agent routing (6 specialist agents)
- SQLModel persistence (conversation history, user profiles)
- ChromaDB RAG with 23+ seeded documents (vs basic SQLite)
- Portfolio analysis, tax planning, and stress testing capabilities
