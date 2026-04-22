"""
Compliance router — SEBI RIA audit trail and reporting endpoints.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.services.compliance import generate_compliance_report

router = APIRouter()


class ComplianceReportRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


@router.post("/report")
async def get_compliance_report(
    body: ComplianceReportRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Generate SEBI-format compliance report for the authenticated user."""
    end = body.end_date or date.today()
    start = body.start_date or (end - timedelta(days=365))
    return await generate_compliance_report(auth.user_id, start, end)


@router.get("/ai-disclosure")
async def ai_disclosure():
    """Public AI disclosure endpoint — SEBI Master Circular requirement."""
    return {
        "platform": "CREDA",
        "ai_disclosure": (
            "CREDA uses artificial intelligence (LLaMA 3.3 70B via Groq) to generate financial analysis and suggestions. "
            "All AI-generated advice is logged with timestamps, user context, and suitability rationale. "
            "CREDA is NOT a SEBI-registered Investment Advisor (RIA). "
            "Users should consult a SEBI-registered advisor before making investment decisions. "
            "AI tools are used for: intent classification, financial analysis, natural language synthesis, and voice processing."
        ),
        "data_handling": "User data is stored in encrypted PostgreSQL databases. Advice logs are retained for 5 years per SEBI guidelines.",
        "model_details": {
            "primary": "LLaMA 3.3 70B (via Groq API)",
            "fast": "LLaMA 3.1 8B Instant (via Groq API)",
            "stt": "faster-whisper (local) / Groq Whisper API",
            "tts": "Kokoro TTS / Edge TTS / Piper TTS",
        },
        "last_updated": "2026-04-22",
    }
