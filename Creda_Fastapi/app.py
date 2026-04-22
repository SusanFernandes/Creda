# CREDA API Gateway
# Intelligent routing layer for FastAPI microservices

from fastapi import FastAPI, Form, HTTPException, UploadFile, File, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from twilio.twiml.voice_response import VoiceResponse
import httpx
import asyncio
import json
import os
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from contextlib import asynccontextmanager
from pydantic import BaseModel
import time
from datetime import datetime
import uvicorn
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: startup and shutdown events"""
    # Startup
    logger.info("🚀 CREDA API Gateway starting up...")
    logger.info(f"📡 Waiting for backend services to be ready...")
    
    # Poll for services with retry logic
    max_retries = 15
    retry_interval = 2  # seconds
    services_ready = {"multilingual": False, "finance": False}
    
    for attempt in range(1, max_retries + 1):
        tasks = []
        
        if not services_ready["multilingual"]:
            tasks.append(check_service_health(FASTAPI1_URL, "multilingual"))
        if not services_ready["finance"]:
            tasks.append(check_service_health(FASTAPI2_URL, "finance"))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check multilingual service
            if not services_ready["multilingual"]:
                multi_healthy = await check_service_health(FASTAPI1_URL, "multilingual")
                if multi_healthy:
                    services_ready["multilingual"] = True
                    logger.info(f"✅ Multilingual Service is READY ({FASTAPI1_URL})")
            
            # Check finance service
            if not services_ready["finance"]:
                finance_healthy = await check_service_health(FASTAPI2_URL, "finance")
                if finance_healthy:
                    services_ready["finance"] = True
                    logger.info(f"✅ Finance Service is READY ({FASTAPI2_URL})")
            
            # All services ready
            if services_ready["multilingual"] and services_ready["finance"]:
                logger.info(f"✅ Gateway ready on port {GATEWAY_PORT}")
                logger.info(f"✅ All services online and ready!")
                break
            
            # Not all ready yet
            if attempt < max_retries:
                ready_count = sum(services_ready.values())
                logger.info(f"⏳ Attempt {attempt}/{max_retries}: {ready_count}/2 services ready. Retrying in {retry_interval}s...")
                await asyncio.sleep(retry_interval)
        else:
            # All services ready on first check
            logger.info(f"✅ Gateway ready on port {GATEWAY_PORT}")
            break
    
    # Log final status
    if not all(services_ready.values()):
        ready_services = [name for name, ready in services_ready.items() if ready]
        unavailable = [name for name, ready in services_ready.items() if not ready]
        logger.warning(f"⚠️  Gateway starting with incomplete backend services!")
        logger.warning(f"   ✅ Ready: {ready_services if ready_services else 'None'}")
        logger.warning(f"   ❌ Unavailable: {unavailable}")
        logger.warning(f"   ℹ️  Gateway will route to available services only.")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 CREDA API Gateway shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="CREDA API Gateway",
    description="Intelligent routing layer for CREDA multilingual finance services",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
FASTAPI1_URL = os.getenv("FASTAPI1_URL", "http://localhost:8000")  # Multilingual service
FASTAPI2_URL = os.getenv("FASTAPI2_URL", "http://localhost:8001")  # Finance service
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8080"))

# Security
security = HTTPBearer(auto_error=False)

# Service health status
service_health = {
    "multilingual": {"status": "unknown", "last_check": None},
    "finance": {"status": "unknown", "last_check": None}
}
# Conversation state management for Indian financial context
conversation_states = {}

class IndianFinancialContext:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.region = "north"  # default
        self.language_preference = "hindi"
        self.financial_profile = {}
        self.recent_queries = []
        self.scheme_interests = []
        
    def update_context(self, query: str, response: dict):
        self.recent_queries.append({
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "intent": response.get("intent", "unknown")
        })
        
        # Keep only last 5 queries
        if len(self.recent_queries) > 5:
            self.recent_queries.pop(0)
# Request models
class QueryRequest(BaseModel):
    query: str
    language: Optional[str] = "english"
    user_id: Optional[str] = None

class PortfolioRequest(BaseModel):
    investment_amount: float
    risk_tolerance: str
    investment_horizon: int
    preferences: Optional[Dict] = None

class VoiceProcessRequest(BaseModel):
    language: Optional[str] = "hindi"
    response_language: Optional[str] = "hindi"

class TranslationRequest(BaseModel):
    text: str
    source_language: str
    target_language: str

# Response models
class GatewayResponse(BaseModel):
    success: bool
    data: Any
    service: str
    timestamp: str
    processing_time: float

class HealthResponse(BaseModel):
    gateway_status: str
    services: Dict[str, Dict]
    timestamp: str

# Utility functions
async def check_service_health(service_url: str, service_name: str) -> bool:
    """Check if a service is healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url}/health")
            is_healthy = response.status_code == 200
            service_health[service_name] = {
                "status": "healthy" if is_healthy else "unhealthy",
                "last_check": datetime.now().isoformat()
            }
            return is_healthy
    except Exception as e:
        logger.error(f"Health check failed for {service_name}: {e}")
        service_health[service_name] = {
            "status": "unhealthy",
            "last_check": datetime.now().isoformat(),
            "error": str(e)
        }
        return False

async def route_request(service_url: str, endpoint: str, method: str = "POST", 
                       data: Any = None, files: Dict = None, params: Dict = None):
    """Route request to appropriate service. Returns dict for JSON or Response for binary."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{service_url}{endpoint}"
            
            # Debug logging
            logger.info(f"Routing {method} request to {url}")
            logger.info(f"Data: {data}")
            logger.info(f"Params: {params}")
            
            if method.upper() == "GET":
                response = await client.get(url, params=params)
            elif method.upper() == "POST":
                if files:
                    # For file uploads, use form data
                    response = await client.post(url, data=data or {}, files=files, params=params)
                elif params and not data:
                    # For query parameters only, use params
                    response = await client.post(url, params=params)
                else:
                    # For JSON data, use json (default case)
                    response = await client.post(url, json=data)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Check content type — don't call .json() on binary responses
                content_type = response.headers.get("content-type", "")
                if any(ct in content_type for ct in ("audio/", "application/octet-stream", "image/", "video/")):
                    # Return a FastAPI Response with raw bytes for binary content
                    return Response(content=response.content, media_type=content_type)
                return response.json()
            elif response.status_code == 422:
                error_detail = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                logger.error(f"Validation error for {endpoint}: {error_detail}")
                raise HTTPException(status_code=422, detail=f"Validation error: {error_detail}")
            else:
                logger.error(f"Service error for {endpoint}: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except httpx.ConnectError:
        logger.error(f"Cannot connect to service: {service_url}")
        raise HTTPException(status_code=503, detail="Service unavailable")
    except HTTPException:
        # Preserve the original status code (e.g. 501 from pipecat, 422 from validation)
        raise
    except Exception as e:
        logger.error(f"Routing error for {endpoint}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal routing error: {str(e)}")

def determine_service_route(endpoint: str, request_data: Any = None) -> tuple:
    """Intelligent routing logic"""
    # Voice and language processing routes -> FastAPI 1
    voice_routes = [
        "/process_voice", "/get_audio_response", "/translate",
        "/understand_intent", "/process_multilingual_query", "/test_asr",
        "/voice/command", "/tts_only", "/transcribe_only",
        "/pipecat/offer",
    ]
    
    # Finance and portfolio routes -> FastAPI 2
    finance_routes = [
        "/process_request", "/get_portfolio_allocation", "/rag_query",
        "/knowledge_base_stats", "/chat", "/profile/upsert",
        "/portfolio/xray", "/portfolio/stress-test", "/fire-planner",
        "/money-health-score", "/tax-wizard", "/sip-calculator",
        "/couples-planner", "/twilio/brain", "/supported_features",
        "/budget/optimize", "/portfolio/optimize", "/portfolio/check-rebalance",
    ]
    
    if endpoint in voice_routes:
        return FASTAPI1_URL, "multilingual"
    elif endpoint in finance_routes:
        return FASTAPI2_URL, "finance"
    else:
        # Intelligent content-based routing
        if request_data:
            content = str(request_data).lower()
            finance_keywords = [
                "portfolio", "investment", "stock", "mutual fund", "risk", "return",
                "allocation", "budget", "financial", "market", "equity", "debt"
            ]
            if any(keyword in content for keyword in finance_keywords):
                return FASTAPI2_URL, "finance"
        
        # Default to multilingual service for unknown routes
        return FASTAPI1_URL, "multilingual"

# Gateway endpoints

@app.get("/")
async def gateway_home():
    """Gateway home endpoint"""
    return {
        "service": "CREDA API Gateway",
        "version": "2.0.0",
        "description": "AI-powered multilingual financial advisory platform",
        "services": {
            "multilingual": FASTAPI1_URL,
            "finance": FASTAPI2_URL
        },
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def gateway_health():
    """Comprehensive health check"""
    # Check both services
    multilingual_healthy = await check_service_health(FASTAPI1_URL, "multilingual")
    finance_healthy = await check_service_health(FASTAPI2_URL, "finance")
    
    gateway_status = "healthy" if multilingual_healthy and finance_healthy else "degraded"
    
    return HealthResponse(
        gateway_status=gateway_status,
        services=service_health,
        timestamp=datetime.now().isoformat()
    )

@app.get("/services")
async def list_services():
    """List all available services and their endpoints"""
    return {
        "multilingual_service": {
            "url": FASTAPI1_URL,
            "endpoints": [
                "/process_voice", "/process_text", "/translate",
                "/tts_only", "/transcribe_only",
                "/health", "/supported_languages",
                "/get_audio_response", "/understand_intent",
                "/process_multilingual_query", "/test_asr"
            ]
        },
        "finance_service": {
            "url": FASTAPI2_URL,
            "endpoints": [
                "/chat", "/profile/upsert", "/profile/{user_id}",
                "/portfolio/xray", "/portfolio/stress-test", "/portfolio/history/{user_id}",
                "/fire-planner", "/money-health-score", "/tax-wizard",
                "/sip-calculator", "/couples-planner", "/twilio/brain",
                "/rag_query", "/knowledge_base_stats", "/supported_features",
                "/process_request", "/get_portfolio_allocation",
            ]
        }
    }

# Voice and Language Processing Routes

@app.post("/process_voice")
async def process_voice_request(audio: UploadFile = File(...), language: str = "hindi"):
    """
    Main endpoint: Process voice input and return voice response
    
    Input: Audio file (WAV/MP3) and optional language parameter
    Output: JSON with response text and audio file
    """
    start_time = time.time()
    try:
        # Read uploaded content and forward to multilingual service
        content = await audio.read()
        files = {
            "audio": (audio.filename or "audio", content, audio.content_type or "application/octet-stream")
        }
        data = {"language": language}

        # Proxy the request to FastAPI1 (multilingual service)
        result = await route_request(FASTAPI1_URL, "/process_voice", "POST", data=data, files=files)

        return GatewayResponse(
            success=True,
            data=result,
            service="multilingual",
            timestamp=datetime.now().isoformat(),
            processing_time=time.time() - start_time
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /process_voice proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/command")
async def voice_command_proxy(
    audio: UploadFile = File(...),
    language_code: str = Form(default="en"),
    current_screen: str = Form(default="dashboard"),
    user_id: str = Form(default="anonymous"),
):
    """
    Push-to-talk command endpoint.
    Proxies to multilingual service /voice/command.
    Returns structured JSON: {transcript, type, function?, args?, response?}
    """
    try:
        content = await audio.read()
        files = {
            "audio": (audio.filename or "audio.wav", content, audio.content_type or "audio/wav")
        }
        data = {
            "language_code": language_code,
            "current_screen": current_screen,
            "user_id": user_id,
        }
        return await route_request(FASTAPI1_URL, "/voice/command", "POST", data=data, files=files)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /voice/command proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipecat/offer")
async def pipecat_offer_proxy(request: Request):
    """
    WebRTC signaling: proxy the browser SDP offer to the multilingual service.
    The multilingual service returns a SDP answer and starts a Pipecat pipeline.
    Requires pipecat-ai[webrtc,silero] installed on the backend.

    Request body (JSON):
      { sdp, type, language_code?, user_id?, current_screen? }
    Response (JSON):
      { sdp, type, pc_id }
    """
    try:
        body = await request.json()
        return await route_request(FASTAPI1_URL, "/pipecat/offer", "POST", data=body)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /pipecat/offer proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_audio_response")
async def get_audio_response(request_data: dict):
    """Route audio response generation to multilingual service"""
    start_time = time.time()

    result = await route_request(FASTAPI1_URL, "/get_audio_response", "POST", data=request_data)
    
    return GatewayResponse(
        success=True,
        data=result,
        service="multilingual",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

@app.post("/translate")
async def translate(request: TranslationRequest):
    """Route translation to multilingual service"""
    start_time = time.time()
    
    # Use POST with JSON body instead of query parameters
    data = {
        "text": request.text,
        "source_language": request.source_language,
        "target_language": request.target_language
    }
    
    result = await route_request(FASTAPI1_URL, "/translate", "POST", data=data)
    
    return GatewayResponse(
        success=True,
        data=result,
        service="multilingual",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

@app.post("/understand_intent")
async def understand_intent(request_data: dict):
    """Route intent understanding to multilingual service"""
    start_time = time.time()
    
    result = await route_request(FASTAPI1_URL, "/understand_intent", "POST", data=request_data)
    
    return GatewayResponse(
        success=True,
        data=result,
        service="multilingual",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

@app.post("/process_multilingual_query")
async def process_multilingual_query(request: QueryRequest):
    """Route multilingual query processing"""
    start_time = time.time()
    
    multilingual_data = {
        "text": request.query,
        "language": request.language,
        "user_id": request.user_id,
        "auto_detect": True
    }
    result = await route_request(FASTAPI1_URL, "/process_multilingual_query", "POST", data=multilingual_data)
    
    return GatewayResponse(
        success=True,
        data=result,
        service="multilingual",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

# Finance and Portfolio Routes

@app.post("/process_request")
async def process_finance_request(request: QueryRequest):
    """Enhanced finance request — routes to v2.0 /chat or /process_request"""
    start_time = time.time()
    
    try:
        # Route to v2 chat API
        chat_data = {
            "message": request.query,
            "user_id": request.user_id or "anonymous",
            "language": request.language or "en",
        }
        result = await route_request(FASTAPI2_URL, "/chat", "POST", data=chat_data)
        service_used = "finance"
    except HTTPException as e:
        logger.warning(f"Finance v2 chat failed: {e}")
        # Fallback to multilingual
        try:
            basic_data = {
                "text": request.query,
                "auto_detect": True,
                "language": request.language,
            }
            result = await route_request(FASTAPI1_URL, "/process_multilingual_query", "POST", data=basic_data)
            service_used = "multilingual (fallback)"
        except HTTPException:
            raise e
    
    return GatewayResponse(
        success=True,
        data=result,
        service=service_used,
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )
    
@app.post("/portfolio_optimization")
async def portfolio_optimization(request: PortfolioRequest):
    """Route portfolio optimization to finance service v2.0 /chat endpoint."""
    start_time = time.time()
    
    # Map old-style request to v2.0 chat API
    risk_tolerance_map = {
        "conservative": 2, "moderate": 3, "balanced": 3,
        "aggressive": 4, "high": 5, "low": 1,
    }
    risk_int = risk_tolerance_map.get(request.risk_tolerance.lower(), 3)
    preferences = request.preferences or {}

    chat_data = {
        "message": (
            f"Optimise my portfolio: ₹{request.investment_amount:,.0f} to invest, "
            f"{request.risk_tolerance} risk, {request.investment_horizon} year horizon."
        ),
        "user_id": preferences.get("user_id", "anonymous"),
        "language": "en",
        "user_profile": {
            "age": preferences.get("age", 30),
            "income": preferences.get("income", max(request.investment_amount * 2, 50000)),
            "savings": request.investment_amount,
            "dependents": preferences.get("dependents", 1),
            "risk_tolerance": risk_int,
            "goal_type": preferences.get("goal_type", "growth"),
            "time_horizon": request.investment_horizon,
        },
    }

    result = await route_request(FASTAPI2_URL, "/chat", "POST", data=chat_data)
    
    return GatewayResponse(
        success=True,
        data=result,
        service="finance",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

@app.post("/rag_query")
async def rag_query(request_data: dict):
    """Route RAG queries to finance service"""
    start_time = time.time()
    
    # Handle both dict and string inputs
    if isinstance(request_data, dict):
        query_text = request_data.get("query", str(request_data))
        top_k = request_data.get("top_k", 5)
    else:
        query_text = str(request_data)
        top_k = 5
    
    # Convert to query parameters for FastAPI2 compatibility
    params = {
        "query": query_text,
        "top_k": top_k
    }
    
    result = await route_request(FASTAPI2_URL, "/rag_query", "POST", params=params)
    
    return GatewayResponse(
        success=True,
        data=result,
        service="finance",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

@app.get("/knowledge_base_stats")
async def knowledge_base_stats():
    """Route knowledge base stats to finance service"""
    start_time = time.time()
    
    result = await route_request(FASTAPI2_URL, "/knowledge_base_stats", "GET")
    
    return GatewayResponse(
        success=True,
        data=result,
        service="finance",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

# Intelligent Universal Endpoint
@app.post("/query")
async def universal_query(request: QueryRequest):
    """Universal query endpoint with intelligent routing"""
    start_time = time.time()
    
    service_url, service_name = determine_service_route("/query", request.dict())
    
    try:
        if service_name == "finance":
            # Format for finance service
            finance_data = {
                "text": request.query,  # Use "text" not "query"
                "intent": "general_query",
                "entities": {},
                "user_language": request.language or "english"
            }
            result = await route_request(service_url, "/process_request", "POST", data=finance_data)
        else:
            # Format for multilingual service
            multilingual_data = {
                "text": request.query,
                "auto_detect": True,
                "language": request.language
            }
            result = await route_request(service_url, "/process_multilingual_query", "POST", data=multilingual_data)
        
        return GatewayResponse(
            success=True,
            data=result,
            service=service_name,
            timestamp=datetime.now().isoformat(),
            processing_time=time.time() - start_time
        )
    except HTTPException as e:
        # Fallback to other service if primary fails
        fallback_url = FASTAPI1_URL if service_name == "finance" else FASTAPI2_URL
        fallback_service = "multilingual" if service_name == "finance" else "finance"
        fallback_endpoint = "/process_multilingual_query" if service_name == "finance" else "/process_request"
        
        try:
            result = await route_request(fallback_url, fallback_endpoint, "POST", data=request.dict())
            
            return GatewayResponse(
                success=True,
                data=result,
                service=f"{fallback_service} (fallback)",
                timestamp=datetime.now().isoformat(),
                processing_time=time.time() - start_time
            )
        except:
            raise e

# Special endpoint for raw string RAG queries
@app.post("/rag_query_text")
async def rag_query_text(request: Request):
    """Route raw text RAG queries to finance service"""
    start_time = time.time()
    
    # Handle both JSON string and raw text input
    try:
        content_type = request.headers.get('content-type', '')
        if 'application/json' in content_type:
            # Handle JSON string input
            raw_data = await request.json()
            if isinstance(raw_data, str):
                query = raw_data
            else:
                # If it's an object, assume it has a query field
                query = raw_data.get('query', str(raw_data))
        else:
            # Handle raw text input
            query = (await request.body()).decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid input format: {str(e)}")
    
    params = {
        "query": query,
        "top_k": 5
    }
    
    result = await route_request(FASTAPI2_URL, "/rag_query", "POST", params=params)
    
    return GatewayResponse(
        success=True,
        data=result,
        service="finance",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

# Additional portfolio endpoint that accepts UserProfile directly
@app.post("/get_portfolio_allocation")
async def get_portfolio_allocation(user_profile: dict):
    """Route portfolio allocation directly to finance service"""
    start_time = time.time()
    
    result = await route_request(FASTAPI2_URL, "/get_portfolio_allocation", "POST", data=user_profile)
    
    return GatewayResponse(
        success=True,
        data=result,
        service="finance",
        timestamp=datetime.now().isoformat(),
        processing_time=time.time() - start_time
    )

# ─────────────────────────────────────────────────────────────────────
# NEW v2.0 GATEWAY ROUTES — Finance Service (LangGraph-powered)
# ─────────────────────────────────────────────────────────────────────

@app.post("/chat")
async def gateway_chat(request_data: dict):
    """Main chat endpoint — routes to finance service LangGraph."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/chat", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/portfolio/xray")
async def gateway_portfolio_xray(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    password: str = Form(default=""),
    language: str = Form(default="en"),
):
    """CAMS PDF X-Ray — streams to finance service."""
    start_time = time.time()
    content = await file.read()
    files = {"file": (file.filename, content, "application/pdf")}
    data = {"password": password, "user_id": user_id, "language": language}
    result = await route_request(FASTAPI2_URL, "/portfolio/xray", "POST", data=data, files=files)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/portfolio/stress-test")
async def gateway_stress_test(request_data: dict):
    """Life event stress test."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/portfolio/stress-test", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/fire-planner")
async def gateway_fire_planner(request_data: dict):
    """FIRE path planner."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/fire-planner", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/money-health-score")
async def gateway_money_health(request_data: dict):
    """6-dimension financial health score."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/money-health-score", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/tax-wizard")
async def gateway_tax_wizard(request_data: dict):
    """Tax regime comparison."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/tax-wizard", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/sip-calculator")
async def gateway_sip(request_data: dict):
    """SIP growth calculator."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/sip-calculator", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/couples-planner")
async def gateway_couples(request_data: dict):
    """Joint financial planning for couples — both partners' data."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/couples-planner", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/budget/optimize")
async def gateway_budget_optimize(request_data: dict):
    """AI-powered budget optimisation."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/budget/optimize", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/portfolio/optimize")
async def gateway_portfolio_optimize(request_data: dict):
    """AI-powered portfolio optimisation."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/portfolio/optimize", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/portfolio/check-rebalance")
async def gateway_portfolio_rebalance(request_data: dict):
    """Portfolio rebalancing check."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/portfolio/check-rebalance", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/twilio/brain")
async def gateway_twilio_brain(request: Request):
    """Brain endpoint for Twilio calling agent."""
    start_time = time.time()
    form_data = await request.form()
    result = await route_request(FASTAPI2_URL, "/twilio/brain", "POST", data=dict(form_data))
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.post("/twilio/voice")
async def gateway_twilio_voice(request: Request):
    """Incoming Twilio voice call handler — routes to finance service.
    
    Returns raw TwiML XML (not wrapped in GatewayResponse).
    """
    form_data = await request.form()
    
    # Route to finance service
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{FASTAPI2_URL}/twilio/voice",
                data=dict(form_data),
                timeout=10
            )
            # Return raw TwiML response (not JSON wrapped)
            return Response(content=response.text, media_type="application/xml")
        except Exception as e:
            logger.error(f"Twilio voice gateway error: {e}")
            # Return error TwiML
            error_response = VoiceResponse()
            error_response.say("Sorry, we're experiencing technical difficulties. Please try again.", voice="Polly.Aditi", language="en-IN")
            error_response.hangup()
            return Response(content=str(error_response), media_type="application/xml")

@app.post("/twilio/process_speech")
async def gateway_twilio_process_speech(request: Request):
    """Process user speech from Twilio Gather — routes to finance service.
    
    Returns raw TwiML XML (not wrapped in GatewayResponse).
    """
    form_data = await request.form()
    
    # Route to finance service
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{FASTAPI2_URL}/twilio/process_speech",
                data=dict(form_data),
                timeout=10
            )
            # Return raw TwiML response (not JSON wrapped)
            return Response(content=response.text, media_type="application/xml")
        except Exception as e:
            logger.error(f"Twilio process_speech gateway error: {e}")
            # Return error TwiML
            error_response = VoiceResponse()
            error_response.say("Sorry, I didn't understand that. Please try again.", voice="Polly.Aditi", language="en-IN")
            error_response.hangup()
            return Response(content=str(error_response), media_type="application/xml")

@app.post("/profile/upsert")
async def gateway_profile_upsert(request_data: dict):
    """Create or update user profile."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/profile/upsert", "POST", data=request_data)
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.get("/profile/{user_id}")
async def gateway_profile_get(user_id: str):
    """Get user profile."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, f"/profile/{user_id}", "GET")
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.get("/portfolio/history/{user_id}")
async def gateway_portfolio_history(user_id: str):
    """Portfolio net worth timeline."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, f"/portfolio/history/{user_id}", "GET")
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

@app.get("/supported_features")
async def gateway_supported_features():
    """Feature list for both products."""
    start_time = time.time()
    result = await route_request(FASTAPI2_URL, "/supported_features", "GET")
    return GatewayResponse(
        success=True, data=result, service="finance",
        timestamp=datetime.now().isoformat(), processing_time=time.time() - start_time
    )

# Dynamic routing for any endpoint

@app.api_route("/{endpoint:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def dynamic_route(endpoint: str, request: Request):
    """Dynamic routing for any endpoint"""
    start_time = time.time()
    
    method = request.method
    
    # Get request data
    if method in ["POST", "PUT"]:
        try:
            request_data = await request.json()
        except:
            request_data = None
    else:
        request_data = dict(request.query_params)
    
    # Determine service
    service_url, service_name = determine_service_route(f"/{endpoint}", request_data)
    
    try:
        result = await route_request(service_url, f"/{endpoint}", method, data=request_data)
        
        # If route_request returned a Response (binary content), pass it through directly
        if isinstance(result, Response):
            return result

        return GatewayResponse(
            success=True,
            data=result,
            service=service_name,
            timestamp=datetime.now().isoformat(),
            processing_time=time.time() - start_time
        )
    except HTTPException as e:
        # Don't re-raise as 500, preserve original error
        logger.error(f"Dynamic routing failed for /{endpoint}: {e}")
        raise e  # This maintains the original status code


# Error handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=GATEWAY_PORT,
        reload=True,
        log_level="info"
    )