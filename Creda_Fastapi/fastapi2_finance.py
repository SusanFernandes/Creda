"""
CREDA Finance Service v2.0 — Port 8001
AI-powered financial advisory backend serving both CREDA and ET PS9.
Orchestrated by LangGraph, persisted with SQLite via SQLModel.

Run:  python fastapi2_finance.py
Docs: http://localhost:8001/docs
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine, select
from twilio.twiml.voice_response import VoiceResponse, Gather

load_dotenv()

# ─── Local imports ────────────────────────────────────────────────────────────
from models import ConversationMessage, LifeEvent, PortfolioSnapshot, UserProfile
from agents.portfolio_xray_agent import compute_portfolio_xirr, parse_cams_pdf, compute_portfolio_overlap, compute_expense_drag, compute_benchmark_comparison
from agents.rag_agent import init_rag

# Lazy import of the compiled graph to avoid heavy import at module level
_financial_graph = None

def _get_graph():
    global _financial_graph
    if _financial_graph is None:
        from agents.graph import financial_graph
        _financial_graph = financial_graph
    return _financial_graph


# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("creda.finance")

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./creda.db")
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.time()
    print("\n" + "=" * 70)
    print("  CREDA Finance Service v2.0")
    print("  Initialising…")
    print("=" * 70)

    # 1. Database
    print("  [1/3] Creating database tables…")
    SQLModel.metadata.create_all(engine)
    print("        ✓ SQLite ready")

    # 2. RAG
    print("  [2/3] Initialising RAG knowledge base…")
    try:
        init_rag()
        print("        ✓ RAG ready")
    except Exception as e:
        logger.error("RAG init failed: %s", e)
        print(f"        ✗ RAG failed: {e}")

    # 3. LangGraph
    print("  [3/3] Compiling LangGraph agent graph…")
    try:
        _get_graph()
        print("        ✓ Agents ready")
    except Exception as e:
        logger.error("Graph compilation failed: %s", e)
        print(f"        ✗ Graph failed: {e}")

    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print(f"  ✅ FINANCE SERVICE READY in {elapsed:.1f}s")
    print("  Listening on http://0.0.0.0:8001")
    print("  Docs: http://0.0.0.0:8001/docs")
    print("=" * 70 + "\n")

    yield

    print("Finance Service shutting down.")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CREDA Finance Service",
    description="AI financial advisory for Indian users — CREDA + ET PS9",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
#  PYDANTIC REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None
    language: Optional[str] = "en"
    user_profile: Optional[Dict[str, Any]] = {}
    portfolio_data: Optional[Dict[str, Any]] = {}


class UserProfileRequest(BaseModel):
    user_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    income: Optional[float] = None
    expenses: Optional[float] = None
    savings: Optional[float] = None
    dependents: Optional[int] = 0
    risk_tolerance: Optional[int] = 3
    goal_type: Optional[str] = "growth"
    time_horizon: Optional[int] = 10
    language: Optional[str] = "en"
    monthly_emi: Optional[float] = 0
    emergency_fund: Optional[float] = 0
    life_insurance_cover: Optional[float] = 0
    has_health_insurance: Optional[bool] = False
    investments_80c: Optional[float] = 0
    nps_contribution: Optional[float] = 0
    health_insurance_premium: Optional[float] = 0
    hra: Optional[float] = 0
    home_loan_interest: Optional[float] = 0
    target_retirement_age: Optional[int] = 60


class MoneyHealthRequest(BaseModel):
    user_id: str = "anonymous"
    language: Optional[str] = "en"


class StressTestRequest(BaseModel):
    user_id: str
    event_type: str
    event_details: Optional[Dict[str, Any]] = {}


class TaxWizardRequest(BaseModel):
    user_id: str
    annual_income: float
    deductions: Optional[Dict[str, Any]] = {}


class CouplesRequest(BaseModel):
    user_id_1: str = ""
    user_id_2: str = ""
    # Accept frontend field names as aliases
    partner1_user_id: Optional[str] = None
    partner2_user_id: Optional[str] = None
    partner_1: Optional[Dict[str, Any]] = {}
    partner_2: Optional[Dict[str, Any]] = {}
    combined_goals: Optional[List[str]] = []
    combined_goal: Optional[str] = None  # frontend sends singular form

    def get_user_id_1(self) -> str:
        return self.user_id_1 or self.partner1_user_id or "anonymous"

    def get_user_id_2(self) -> str:
        return self.user_id_2 or self.partner2_user_id or "anonymous"


class FIREPlannerRequest(BaseModel):
    """Accepts both ChatRequest format and frontend FIRERequest format."""
    user_id: str = "anonymous"
    message: Optional[str] = None
    session_id: Optional[str] = None
    language: Optional[str] = "en"
    user_profile: Optional[Dict[str, Any]] = {}
    portfolio_data: Optional[Dict[str, Any]] = {}
    # Frontend FIRERequest fields
    monthly_expenses: Optional[float] = None
    current_savings: Optional[float] = None
    monthly_investment: Optional[float] = None
    expected_return: Optional[float] = None
    inflation_rate: Optional[float] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER — run the LangGraph
# ═══════════════════════════════════════════════════════════════════════════════

async def _run_graph(
    message: str,
    user_id: str,
    session_id: str,
    language: str = "en",
    user_profile: Optional[Dict] = None,
    portfolio_data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Central helper that invokes the LangGraph financial agent graph."""
    graph = _get_graph()

    # ── Load persisted profile if caller didn't supply one ──
    if not user_profile:
        with Session(engine) as sess:
            profile_row = sess.exec(
                select(UserProfile).where(UserProfile.user_id == user_id)
            ).first()
            if profile_row:
                user_profile = {
                    c.name: getattr(profile_row, c.name)
                    for c in UserProfile.__table__.columns  # type: ignore[attr-defined]
                    if c.name not in ("id", "created_at", "updated_at")
                }
    user_profile = user_profile or {}
    portfolio_data = portfolio_data or {}

    # ── Load conversation history ──
    with Session(engine) as sess:
        history_rows = sess.exec(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.timestamp)  # type: ignore[arg-type]
        ).all()

    messages: List[HumanMessage] = []
    for msg in (history_rows or [])[-6:]:
        messages.append(HumanMessage(content=msg.content))
    messages.append(HumanMessage(content=message))

    initial_state = {
        "messages": messages,
        "user_id": user_id,
        "session_id": session_id,
        "language": language,
        "user_profile": user_profile,
        "portfolio_data": portfolio_data,
        "intent": "",
        "agent_outputs": {},
        "final_response": "",
        "response_data": {},
    }

    try:
        result = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("LangGraph invocation failed: %s", e, exc_info=True)
        result = {
            "final_response": "I understand your question but encountered an error. Please try again.",
            "agent_outputs": {},
            "intent": "general_chat",
        }

    # ── Persist conversation turn ──
    with Session(engine) as sess:
        sess.add(ConversationMessage(
            session_id=session_id, user_id=user_id,
            role="user", content=message,
        ))
        sess.add(ConversationMessage(
            session_id=session_id, user_id=user_id,
            role="assistant", content=result.get("final_response", ""),
        ))
        sess.commit()

    return {
        "session_id": session_id,
        "response": result.get("final_response", ""),
        "intent": result.get("intent", ""),
        "data": result.get("agent_outputs", {}),
        "user_id": user_id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {"service": "CREDA Finance Service", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "finance",
        "database": "connected",
        "agents": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  USER PROFILE — PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/profile/upsert")
async def upsert_profile(request: UserProfileRequest):
    """Create or update a user profile (persisted to SQLite)."""
    with Session(engine) as sess:
        existing = sess.exec(
            select(UserProfile).where(UserProfile.user_id == request.user_id)
        ).first()

        data = request.model_dump(exclude_unset=True, exclude={"user_id"})
        if existing:
            for key, val in data.items():
                if val is not None:
                    setattr(existing, key, val)
            existing.updated_at = datetime.now(timezone.utc)
            sess.add(existing)
        else:
            profile = UserProfile(user_id=request.user_id, **data)
            sess.add(profile)
        sess.commit()

    return {"success": True, "user_id": request.user_id, "message": "Profile saved"}


@app.get("/profile/{user_id}")
async def get_profile(user_id: str):
    with Session(engine) as sess:
        profile = sess.exec(
            select(UserProfile).where(UserProfile.user_id == user_id)
        ).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return profile.model_dump()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN CHAT — LANGGRAPH ORCHESTRATED
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Main conversational endpoint.
    Routes to the appropriate specialist agent via LangGraph.
    """
    session_id = request.session_id or str(uuid.uuid4())
    return await _run_graph(
        message=request.message,
        user_id=request.user_id,
        session_id=session_id,
        language=request.language or "en",
        user_profile=request.user_profile,
        portfolio_data=request.portfolio_data,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TWILIO BRAIN
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/twilio/brain")
async def twilio_brain(
    speech_text: str = Form(...),
    session_id: str = Form(...),
    user_id: Optional[str] = Form(default="twilio_user"),
    language: Optional[str] = Form(default="hi"),
):
    """Brain endpoint for Twilio calling agent — receives transcribed speech,
    returns text to be spoken back."""
    result = await _run_graph(
        message=speech_text,
        user_id=user_id or "twilio_user",
        session_id=session_id,
        language=language or "hi",
    )
    return {
        "response_text": result["response"],
        "session_id": session_id,
        "detected_intent": result.get("intent", ""),
        "language": language,
    }


def truncate_for_voice(text: str, max_chars: int = 300) -> str:
    """Truncate text for voice synthesis (Polly has limits).
    Keep responses voice-friendly: under 300 characters (~30 seconds at normal speech rate)."""
    if len(text) > max_chars:
        # Try to break at sentence boundary
        sentences = text.split(". ")
        truncated = ""
        for sentence in sentences:
            if len(truncated) + len(sentence) + 2 <= max_chars:
                truncated += sentence + ". "
            else:
                break
        return truncated.strip() or text[:max_chars]
    return text


def build_voice_response(text: str, gather_timeout: int = 60, language: str = "en-IN") -> str:
    """Build TwiML voice response with Say + Gather.
    
    Args:
        text: Response text to speak
        gather_timeout: How long to wait for user input (seconds)
        language: Language code for Polly (e.g., 'en-IN' for Indian English)
    
    Returns:
        TwiML XML string
    """
    response = VoiceResponse()
    
    # Truncate for voice synthesis
    voice_text = truncate_for_voice(text)
    
    # Say the response using Indian English voice
    response.say(
        voice_text,
        voice="Polly.Aditi",  # Indian English voice
        language=language
    )
    
    # Gather user input (speech)
    gather = Gather(
        input="speech",
        action="/twilio/process_speech",
        method="POST",
        language=language,
        speech_timeout="auto",
        timeout=gather_timeout,
        max_speech_time=60
    )
    gather.say("", voice="Polly.Aditi", language=language)  # Placeholder for next turn
    response.append(gather)
    
    return str(response)


@app.post("/twilio/voice")
async def twilio_voice(
    call_sid: str = Form(...),
    digits: Optional[str] = Form(default=None),
    speech_result: Optional[str] = Form(default=None),
    speech_confidence: Optional[float] = Form(default=None),
):
    """Incoming Twilio voice call handler.
    
    Handles:
    - Initial call greeting (no speech_result)
    - User speech input (speech_result provided)
    - DTMF digits (for menu navigation if needed)
    
    Returns:
        TwiML XML response for Twilio
    """
    user_id = f"voice_{call_sid}"
    session_id = call_sid
    language = "en-IN"
    
    try:
        # Check if this is the first call (no speech input yet)
        if not speech_result:
            # Initial greeting
            greeting = "Welcome to CREDA, your AI financial advisor. How can I help you today? You can ask about taxes, investments, mutual funds, retirement planning, or financial strategies. Please speak now."
            return Response(
                content=build_voice_response(greeting, language=language),
                media_type="application/xml"
            )
        
        # User provided speech input
        user_input = speech_result.strip()
        
        if not user_input:
            # No speech detected
            response_text = "I didn't catch that. Please try again."
            return Response(
                content=build_voice_response(response_text, language=language),
                media_type="application/xml"
            )
        
        # Check for hangup triggers
        if any(word in user_input.lower() for word in ["goodbye", "bye", "end call", "thank you bye", "exit"]):
            response = VoiceResponse()
            response.say(
                "Thank you for calling CREDA. Have a great day! Goodbye.",
                voice="Polly.Aditi",
                language=language
            )
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        
        # Route through LangGraph via _run_graph
        result = await _run_graph(
            message=user_input,
            user_id=user_id,
            session_id=session_id,
            language="en",  # LangGraph uses 'en' internally
        )
        
        ai_response = result.get("response", "Let me help you with that.")
        
        # Store conversation to database
        with Session(engine) as sess:
            sess.add(ConversationMessage(
                session_id=session_id,
                user_id=user_id,
                call_sid=call_sid,
                role="user",
                content=user_input,
                content_type="text"
            ))
            sess.add(ConversationMessage(
                session_id=session_id,
                user_id=user_id,
                call_sid=call_sid,
                role="assistant",
                content=ai_response,
                content_type="text"
            ))
            sess.commit()
        
        # Return TwiML response
        return Response(
            content=build_voice_response(ai_response, language=language),
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error(f"Voice call handler error (call_sid={call_sid}): {str(e)}", exc_info=True)
        response = VoiceResponse()
        response.say(
            "Sorry, I encountered a technical issue. Your call may be recorded for quality improvement. Please try again or call back later.",
            voice="Polly.Aditi",
            language=language
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")


@app.post("/twilio/process_speech")
async def twilio_process_speech(
    speech_result: Optional[str] = Form(default=None),
    call_sid: str = Form(...),
):
    """Webhook for continued voice conversation (called by Gather action).
    
    This endpoint receives the user's speech and routes it back to /twilio/voice
    for processing as if it were a new call with user input.
    """
    # Delegate to main voice handler
    return await twilio_voice(call_sid=call_sid, speech_result=speech_result)


# ═══════════════════════════════════════════════════════════════════════════════
#  MF PORTFOLIO X-RAY (ET PS9 core)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/portfolio/xray")
async def portfolio_xray(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    password: str = Form(default=""),
    language: Optional[str] = Form(default="en"),
):
    """Upload CAMS/KFintech PDF → full X-Ray (XIRR, overlap, expense drag, rebalancing)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    pdf_bytes = await file.read()
    try:
        cas_data = parse_cams_pdf(pdf_bytes, password)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF parsing failed: {e}")

    xray_data = compute_portfolio_xirr(cas_data)

    # Enrich with overlap, expense drag, and benchmark comparison
    if xray_data.get("schemes"):
        from agents.portfolio_xray_agent import compute_portfolio_overlap, compute_expense_drag, compute_benchmark_comparison
        overlap = compute_portfolio_overlap(xray_data["schemes"])
        expense = compute_expense_drag(xray_data["schemes"])
        xray_data["overlap_analysis"] = overlap
        xray_data["expense_drag"] = expense
        try:
            xray_data["benchmark_comparison"] = compute_benchmark_comparison(xray_data["schemes"])
        except Exception as e:
            logger.warning("Benchmark comparison skipped: %s", e)
            xray_data["benchmark_comparison"] = {"error": str(e)}

    # Load profile for rebalancing context
    user_profile: Dict[str, Any] = {}
    with Session(engine) as sess:
        profile_row = sess.exec(
            select(UserProfile).where(UserProfile.user_id == user_id)
        ).first()
        if profile_row:
            user_profile = profile_row.model_dump()

    # Run through LangGraph for narrative + rebalancing
    session_id = f"xray_{user_id}_{datetime.now(timezone.utc).date()}"
    result = await _run_graph(
        message="Analyse my portfolio and give the full X-Ray with rebalancing plan",
        user_id=user_id,
        session_id=session_id,
        language=language or "en",
        user_profile=user_profile,
        portfolio_data=xray_data,
    )

    # Save snapshot
    with Session(engine) as sess:
        sess.add(PortfolioSnapshot(
            user_id=user_id,
            total_invested=xray_data.get("total_invested", 0),
            current_value=xray_data.get("total_current_value", 0),
            xirr=xray_data.get("overall_xirr"),
            holdings_json=json.dumps(xray_data.get("schemes", [])),
            source="cams_pdf",
        ))
        sess.commit()

    return {
        "user_id": user_id,
        "xray": xray_data,
        "rebalancing_plan": result["data"].get("portfolio_xray", {}).get("rebalancing_plan", {}),
        "narrative": result["response"],
        "investor_info": cas_data.get("investor_info", {}),
        "statement_period": cas_data.get("statement_period", {}),
    }


@app.post("/portfolio/stress-test")
async def portfolio_stress_test(request: StressTestRequest):
    """Life-event stress simulation on an existing portfolio."""
    portfolio_data: Dict[str, Any] = {}
    user_profile: Dict[str, Any] = {}

    with Session(engine) as sess:
        snapshot = sess.exec(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == request.user_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())  # type: ignore[arg-type]
        ).first()
        if snapshot:
            portfolio_data = {
                "total_current_value": snapshot.current_value,
                "total_invested": snapshot.total_invested,
                "schemes": json.loads(snapshot.holdings_json),
            }
        profile_row = sess.exec(
            select(UserProfile).where(UserProfile.user_id == request.user_id)
        ).first()
        if profile_row:
            user_profile = profile_row.model_dump()

    return await _run_graph(
        message=f"Stress test my portfolio for life event: {request.event_type}. {json.dumps(request.event_details)}",
        user_id=request.user_id,
        session_id=str(uuid.uuid4()),
        user_profile=user_profile,
        portfolio_data=portfolio_data,
    )


@app.get("/portfolio/history/{user_id}")
async def portfolio_history(user_id: str):
    """Portfolio snapshot history for tracking net worth over time."""
    with Session(engine) as sess:
        snapshots = sess.exec(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user_id)
            .order_by(PortfolioSnapshot.snapshot_date)  # type: ignore[arg-type]
        ).all()
    return {"user_id": user_id, "history": [s.model_dump() for s in snapshots]}


# ═══════════════════════════════════════════════════════════════════════════════
#  ET PS9 ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/fire-planner")
async def fire_planner(request: FIREPlannerRequest):
    """FIRE path planner — full month-by-month roadmap."""
    # Build context message from frontend FIRE fields if no message provided
    fire_context_parts = []
    if request.monthly_expenses is not None:
        fire_context_parts.append(f"monthly expenses ₹{request.monthly_expenses:,.0f}")
    if request.current_savings is not None:
        fire_context_parts.append(f"current savings ₹{request.current_savings:,.0f}")
    if request.monthly_investment is not None:
        fire_context_parts.append(f"monthly investment ₹{request.monthly_investment:,.0f}")
    if request.expected_return is not None:
        fire_context_parts.append(f"expected return {request.expected_return}%")
    if request.inflation_rate is not None:
        fire_context_parts.append(f"inflation {request.inflation_rate}%")

    if request.message:
        message = request.message
    elif fire_context_parts:
        message = (
            "Create my complete FIRE financial roadmap with month-by-month milestones. "
            f"My details: {', '.join(fire_context_parts)}."
        )
    else:
        message = "Create my complete FIRE financial roadmap with month-by-month milestones"

    # Merge FIRE fields into user_profile so agents can use them
    profile = dict(request.user_profile or {})
    if request.monthly_expenses is not None:
        profile.setdefault("expenses", request.monthly_expenses)
    if request.current_savings is not None:
        profile.setdefault("savings", request.current_savings)

    session_id = request.session_id or str(uuid.uuid4())
    return await _run_graph(
        message=message,
        user_id=request.user_id,
        session_id=session_id,
        language=request.language or "en",
        user_profile=profile,
        portfolio_data=request.portfolio_data,
    )


@app.post("/money-health-score")
async def money_health_score(request: MoneyHealthRequest):
    """6-dimension financial health score."""
    user_id = request.user_id
    language = request.language or "en"
    user_profile: Dict[str, Any] = {}
    portfolio_data: Dict[str, Any] = {}

    with Session(engine) as sess:
        profile_row = sess.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
        if profile_row:
            user_profile = profile_row.model_dump()
        snapshot = sess.exec(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())  # type: ignore[arg-type]
        ).first()
        if snapshot:
            portfolio_data = {
                "total_current_value": snapshot.current_value,
                "schemes": json.loads(snapshot.holdings_json),
            }

    return await _run_graph(
        message="Give me my complete money health score across all 6 dimensions",
        user_id=user_id,
        session_id=str(uuid.uuid4()),
        language=language or "en",
        user_profile=user_profile,
        portfolio_data=portfolio_data,
    )


@app.post("/tax-wizard")
async def tax_wizard(request: TaxWizardRequest):
    """Tax regime comparison + missed deductions finder."""
    return await _run_graph(
        message=(
            f"Analyse my taxes. Annual income: ₹{request.annual_income}. "
            f"Deductions: {json.dumps(request.deductions)}. "
            f"Compare old vs new regime and find all missed deductions."
        ),
        user_id=request.user_id,
        session_id=str(uuid.uuid4()),
        user_profile={"income": request.annual_income / 12, **(request.deductions or {})},
    )


@app.post("/couples-planner")
async def couples_planner(request: CouplesRequest):
    """Joint financial planning for couples — optimises across both incomes."""
    # Resolve user IDs from either naming convention
    uid1 = request.get_user_id_1()
    uid2 = request.get_user_id_2()
    # Merge combined_goal into combined_goals list if provided
    goals = list(request.combined_goals or [])
    if request.combined_goal and request.combined_goal not in goals:
        goals.append(request.combined_goal)

    # Load saved profiles if partner data not provided
    p1 = request.partner_1 or {}
    p2 = request.partner_2 or {}

    with Session(engine) as sess:
        if not p1:
            row = sess.exec(select(UserProfile).where(UserProfile.user_id == uid1)).first()
            if row:
                p1 = {c.name: getattr(row, c.name) for c in UserProfile.__table__.columns if c.name not in ("id", "created_at", "updated_at")}
        if not p2:
            row = sess.exec(select(UserProfile).where(UserProfile.user_id == uid2)).first()
            if row:
                p2 = {c.name: getattr(row, c.name) for c in UserProfile.__table__.columns if c.name not in ("id", "created_at", "updated_at")}

    combined_income = (p1.get("income", 0) or 0) + (p2.get("income", 0) or 0)
    combined_expenses = (p1.get("expenses", 0) or 0) + (p2.get("expenses", 0) or 0)
    combined_savings = (p1.get("savings", 0) or 0) + (p2.get("savings", 0) or 0)

    combined_profile = {
        "income": combined_income,
        "expenses": combined_expenses,
        "savings": combined_savings,
        "dependents": max(p1.get("dependents", 0) or 0, p2.get("dependents", 0) or 0),
        "risk_tolerance": min(p1.get("risk_tolerance", 3) or 3, p2.get("risk_tolerance", 3) or 3),
        "age": max(p1.get("age", 30) or 30, p2.get("age", 30) or 30),
        "target_retirement_age": min(p1.get("target_retirement_age", 60) or 60, p2.get("target_retirement_age", 60) or 60),
        "emergency_fund": (p1.get("emergency_fund", 0) or 0) + (p2.get("emergency_fund", 0) or 0),
        "life_insurance_cover": (p1.get("life_insurance_cover", 0) or 0) + (p2.get("life_insurance_cover", 0) or 0),
        "investments_80c": (p1.get("investments_80c", 0) or 0) + (p2.get("investments_80c", 0) or 0),
        "nps_contribution": (p1.get("nps_contribution", 0) or 0) + (p2.get("nps_contribution", 0) or 0),
        "hra": max(p1.get("hra", 0) or 0, p2.get("hra", 0) or 0),
    }

    goals_text = ", ".join(goals) if goals else "retirement, home purchase, child education"

    return await _run_graph(
        message=(
            f"Create an optimised joint financial plan for a couple.\n"
            f"Partner 1: Age {p1.get('age','?')}, Income ₹{p1.get('income',0):,.0f}/month, "
            f"Savings ₹{p1.get('savings',0):,.0f}, 80C used ₹{p1.get('investments_80c',0):,.0f}\n"
            f"Partner 2: Age {p2.get('age','?')}, Income ₹{p2.get('income',0):,.0f}/month, "
            f"Savings ₹{p2.get('savings',0):,.0f}, 80C used ₹{p2.get('investments_80c',0):,.0f}\n"
            f"Combined monthly income: ₹{combined_income:,.0f}\n"
            f"Goals: {goals_text}\n"
            f"Optimise: HRA claims, NPS matching, SIP splits for tax efficiency, "
            f"joint vs individual insurance, combined net worth tracking."
        ),
        user_id=uid1,
        session_id=str(uuid.uuid4()),
        user_profile=combined_profile,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  BUDGET & PORTFOLIO OPTIMIZATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


class BudgetOptimizeRequest(BaseModel):
    user_id: str = "anonymous"
    expenses: Optional[List[Dict[str, Any]]] = []
    language: Optional[str] = "en"
    user_profile: Optional[Dict[str, Any]] = {}


class PortfolioOptimizeRequest(BaseModel):
    user_id: str = "anonymous"
    goals: Optional[List[str]] = []
    time_horizon_years: Optional[int] = 25
    language: Optional[str] = "en"
    profile: Optional[Dict[str, Any]] = {}


class RebalanceCheckRequest(BaseModel):
    user_id: str = "anonymous"
    current_allocation: Optional[Dict[str, Any]] = {}
    threshold: Optional[float] = 0.05
    language: Optional[str] = "en"
    profile: Optional[Dict[str, Any]] = {}


@app.post("/budget/optimize")
async def budget_optimize(request: BudgetOptimizeRequest):
    """AI-powered budget optimisation — analyses expenses and suggests savings."""
    user_id = request.user_id
    user_profile = dict(request.user_profile or {})

    # Load persisted profile if not supplied
    if not user_profile:
        with Session(engine) as sess:
            row = sess.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
            if row:
                user_profile = row.model_dump()

    expenses_text = ""
    if request.expenses:
        expenses_text = "My expenses: " + ", ".join(
            f"{e.get('category', 'other')}: ₹{e.get('amount', 0)}" for e in request.expenses
        )

    message = (
        f"Optimise my monthly budget. {expenses_text} "
        f"Suggest where I can save more and how to reallocate savings to investments."
    )

    return await _run_graph(
        message=message,
        user_id=user_id,
        session_id=str(uuid.uuid4()),
        language=request.language or "en",
        user_profile=user_profile,
    )


@app.post("/portfolio/optimize")
async def portfolio_optimize(request: PortfolioOptimizeRequest):
    """AI-powered portfolio optimisation based on goals and risk profile."""
    user_id = request.user_id
    user_profile = dict(request.profile or {})

    if not user_profile:
        with Session(engine) as sess:
            row = sess.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
            if row:
                user_profile = row.model_dump()

    goals_text = ", ".join(request.goals) if request.goals else "wealth creation, retirement"
    message = (
        f"Optimise my portfolio for these goals: {goals_text}. "
        f"Time horizon: {request.time_horizon_years} years. "
        f"Give specific fund recommendations and allocation percentages."
    )

    return await _run_graph(
        message=message,
        user_id=user_id,
        session_id=str(uuid.uuid4()),
        language=request.language or "en",
        user_profile=user_profile,
    )


@app.post("/portfolio/check-rebalance")
async def portfolio_check_rebalance(request: RebalanceCheckRequest):
    """Check whether portfolio needs rebalancing based on drift threshold."""
    user_id = request.user_id
    user_profile = dict(request.profile or {})
    portfolio_data: Dict[str, Any] = {}

    with Session(engine) as sess:
        if not user_profile:
            row = sess.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
            if row:
                user_profile = row.model_dump()
        snapshot = sess.exec(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())  # type: ignore[arg-type]
        ).first()
        if snapshot:
            portfolio_data = {
                "total_current_value": snapshot.current_value,
                "schemes": json.loads(snapshot.holdings_json),
            }

    alloc_text = ""
    if request.current_allocation:
        alloc_text = "Current allocation: " + ", ".join(
            f"{k}: {v}" for k, v in request.current_allocation.items()
        )

    message = (
        f"Check if my portfolio needs rebalancing. {alloc_text} "
        f"Drift threshold: {request.threshold * 100:.0f}%. "
        f"Give a rebalancing plan if needed."
    )

    return await _run_graph(
        message=message,
        user_id=user_id,
        session_id=str(uuid.uuid4()),
        language=request.language or "en",
        user_profile=user_profile,
        portfolio_data=portfolio_data,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  CREDA UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class SIPRequest(BaseModel):
    monthly_amount: float
    years: int
    expected_return: Optional[float] = 12.0
    user_id: Optional[str] = "anonymous"


@app.post("/sip-calculator")
async def sip_calculator(request: SIPRequest):
    """SIP growth calculator with step-up projection (no LLM call needed)."""
    monthly_amount = request.monthly_amount
    years = request.years
    expected_return = request.expected_return or 12.0
    monthly_rate = expected_return / 100 / 12
    months = years * 12

    # Regular SIP
    if monthly_rate > 0:
        regular = monthly_amount * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    else:
        regular = monthly_amount * months

    # Step-up SIP (10% annual increase)
    stepup = 0.0
    sip = monthly_amount
    for yr in range(years):
        for _ in range(12):
            stepup = stepup * (1 + monthly_rate) + sip
        sip *= 1.10

    total_invested = monthly_amount * months
    return {
        "monthly_sip": monthly_amount,
        "years": years,
        "expected_return_percent": expected_return,
        "total_invested": round(total_invested, 0),
        "regular_corpus": round(regular, 0),
        "stepup_corpus_10pct": round(stepup, 0),
        "absolute_gain_regular": round(regular - total_invested, 0),
        "absolute_gain_stepup": round(stepup - total_invested, 0),
        "wealth_multiplier": round(regular / total_invested, 2) if total_invested else 0,
    }


# ── Backward-compat endpoints so existing gateway routes still work ──

@app.post("/rag_query")
async def rag_query(query: str, top_k: Optional[int] = 5):
    """RAG query — backward compatibility."""
    result = await _run_graph(message=query, user_id="rag_user", session_id=str(uuid.uuid4()))
    return {"answer": result["response"], "sources": result.get("data", {}).get("rag_query", {}).get("sources", [])}


@app.post("/process_request")
async def process_request(request: Dict[str, Any]):
    """Backward compatibility with old finance service contract."""
    message = request.get("text", request.get("query", ""))
    user_id = request.get("user_id", "anonymous")
    language = request.get("user_language", "en")
    return await _run_graph(
        message=message,
        user_id=user_id,
        session_id=str(uuid.uuid4()),
        language=language,
        user_profile=request.get("user_profile", {}),
    )


@app.post("/get_portfolio_allocation")
async def get_portfolio_allocation(request: Dict[str, Any]):
    """Backward compatibility — portfolio allocation via chat."""
    profile = request.get("profile", request)
    return await _run_graph(
        message="Give me my optimal portfolio allocation based on my profile",
        user_id=str(profile.get("user_id", "anonymous")),
        session_id=str(uuid.uuid4()),
        user_profile=profile,
    )


@app.get("/knowledge_base_stats")
async def knowledge_base_stats():
    """RAG knowledge base statistics."""
    try:
        from agents.rag_agent import _collection
        count = _collection.count() if _collection else 0
    except Exception:
        count = 0
    return {
        "total_documents": count,
        "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
        "storage": "ChromaDB (persistent)",
    }


@app.get("/supported_features")
async def supported_features():
    return {
        "creda_features": [
            "voice_chat_multilingual", "sip_calculator", "fire_planner",
            "money_health_score", "budget_coaching", "insurance_check",
            "rag_regulatory_knowledge", "goal_planning",
        ],
        "et_ps9_features": [
            "cams_pdf_xray", "true_xirr_calculation", "overlap_analysis",
            "expense_ratio_drag", "portfolio_stress_test", "life_event_advisor",
            "rebalancing_playbook", "tax_wizard", "couples_planner", "fire_roadmap",
        ],
        "languages": ["en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "ur"],
        "data_sources": ["cams_pdf", "manual_input", "aa_framework_planned"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run("fastapi2_finance:app", host="0.0.0.0", port=8001, reload=True)
