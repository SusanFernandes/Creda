"""
Middleware: BackendClient + async user resolution.
"""
import httpx
from asgiref.sync import iscoroutinefunction, sync_to_async
from django.conf import settings
from django.contrib.auth import get_user as _get_user
from django.contrib.auth.models import AnonymousUser
from django.utils.decorators import sync_and_async_middleware


@sync_and_async_middleware
def async_user_middleware(get_response):
    """
    Pre-resolve request.user for async views.
    Django's AuthenticationMiddleware sets a lazy object that triggers
    a synchronous DB lookup. This middleware resolves it eagerly so
    templates can access request.user.first_name etc. without crashing.
    """
    if iscoroutinefunction(get_response):
        async def middleware(request):
            if hasattr(request, "user") and hasattr(request.user, "_wrapped"):
                try:
                    request.user = await sync_to_async(_get_user)(request)
                except Exception:
                    request.user = AnonymousUser()
            return await get_response(request)
    else:
        def middleware(request):
            return get_response(request)
    return middleware


@sync_and_async_middleware
def backend_client_middleware(get_response):
    """Attach an async BackendClient to each request (sync/async compatible)."""
    _client = httpx.AsyncClient(
        base_url=settings.BACKEND_API_URL,
        timeout=30.0,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )

    if iscoroutinefunction(get_response):
        async def middleware(request):
            request.backend = BackendClient(_client, request)
            response = await get_response(request)
            return response
    else:
        def middleware(request):
            request.backend = BackendClient(_client, request)
            response = get_response(request)
            return response

    return middleware


class BackendClient:
    """
    Typed wrapper around httpx.AsyncClient for FastAPI backend calls.
    Automatically injects x-user-id and x-user-email headers from Django session.
    """

    def __init__(self, client: httpx.AsyncClient, request):
        self._client = client
        self._request = request

    def _headers(self) -> dict[str, str]:
        """Inject auth headers — the JWT link between Django User and FastAPI."""
        user = self._request.user
        headers = {}
        if user.is_authenticated:
            headers["x-user-id"] = str(user.id)
            headers["x-user-email"] = user.email or ""
        # Optionally pass JWT from session
        jwt_token = self._request.session.get("backend_jwt")
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        return headers

    # ── Profile ────────────────────────────────────────────
    async def get_profile(self, user_id: str) -> dict:
        resp = await self._client.get(f"/profile/{user_id}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def upsert_profile(self, data: dict) -> dict:
        resp = await self._client.post("/profile/upsert", json=data, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def is_onboarded(self, user_id: str) -> bool:
        resp = await self._client.get(f"/profile/{user_id}/is-onboarded", headers=self._headers())
        resp.raise_for_status()
        return resp.json().get("onboarded", False)

    # ── Chat ───────────────────────────────────────────────
    async def post_chat(self, message: str, session_id: str = "",
                        language: str = "en", voice_mode: bool = False) -> dict:
        resp = await self._client.post("/chat", json={
            "message": message, "session_id": session_id,
            "language": language, "voice_mode": voice_mode,
        }, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── Portfolio ──────────────────────────────────────────
    async def upload_portfolio(self, pdf_bytes: bytes, filename: str, password: str = "") -> dict:
        files = {"file": (filename, pdf_bytes, "application/pdf")}
        data = {"password": password} if password else {}
        resp = await self._client.post("/portfolio/upload", files=files, data=data, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def get_portfolio_summary(self) -> dict:
        resp = await self._client.get("/portfolio/summary", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def run_xray(self) -> dict:
        resp = await self._client.post("/portfolio/xray", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── Agents (direct endpoints) ──────────────────────────
    async def fire_planner(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/fire-planner", language)

    async def tax_wizard(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/tax-wizard", language)

    async def money_health(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/money-health", language)

    async def stress_test(self, events: list[str], language: str = "en") -> dict:
        resp = await self._client.post("/agents/stress-test", json={
            "events": events, "language": language,
        }, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def budget_coach(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/budget-coach", language)

    async def goal_planner(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/goal-planner", language)

    async def couples_finance(self, partner_income: float = 0, partner_expenses: float = 0,
                               language: str = "en") -> dict:
        resp = await self._client.post("/agents/couples-finance", json={
            "partner_income": partner_income, "partner_expenses": partner_expenses, "language": language,
        }, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def sip_calculator(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/sip-calculator", language)

    # ── ET-Inspired Agents ─────────────────────────────────
    async def market_pulse(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/market-pulse", language)

    async def tax_copilot(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/tax-copilot", language)

    async def money_personality(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/money-personality", language)

    async def goal_simulator(self, target_amount: float = 5000000, years: int = 10,
                              language: str = "en") -> dict:
        resp = await self._client.post("/agents/goal-simulator", json={
            "target_amount": target_amount, "years": years, "language": language,
        }, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def social_proof(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/social-proof", language)

    async def et_research(self, message: str, language: str = "en") -> dict:
        resp = await self._client.post("/agents/et-research", json={
            "message": message, "language": language,
        }, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def human_handoff(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/human-handoff", language)

    # ── Nudges ─────────────────────────────────────────────
    async def get_nudges(self) -> list:
        resp = await self._client.get("/nudges/pending", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def mark_nudge_read(self, nudge_id: str) -> dict:
        resp = await self._client.post(f"/nudges/{nudge_id}/read", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── Health ─────────────────────────────────────────────
    async def health_check(self) -> dict:
        resp = await self._client.get("/health")
        return resp.json()

    # ── Compliance ─────────────────────────────────────────
    async def compliance_report(self, start_date: str = "", end_date: str = "") -> dict:
        payload = {}
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date
        resp = await self._client.post("/compliance/report", json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def ai_disclosure(self) -> dict:
        resp = await self._client.get("/compliance/ai-disclosure")
        return resp.json()

    # ── Family Wealth ──────────────────────────────────────
    async def family_members(self) -> dict:
        resp = await self._client.get("/family/members", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def link_family_member(self, email: str, relationship: str = "spouse") -> dict:
        resp = await self._client.post("/family/link", json={
            "member_email": email, "relationship": relationship,
        }, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def family_wealth(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/family-wealth", language)

    # ── Voice ──────────────────────────────────────────────
    async def voice_chat(self, audio_bytes: bytes, filename: str, language: str = "en") -> dict:
        """Send audio to voice pipeline, return text + audio response."""
        import base64
        files = {"audio": (filename, audio_bytes, "audio/webm")}
        data = {"language": language}
        resp = await self._client.post("/voice/pipeline", files=files, data=data, headers=self._headers())
        resp.raise_for_status()
        # Capture the audio body (WAV bytes) and encode as base64
        audio_b64 = base64.b64encode(resp.content).decode("ascii") if resp.content else ""
        return {
            "response": resp.headers.get("X-Response-Text", ""),
            "transcript": resp.headers.get("X-Transcript", ""),
            "intent": resp.headers.get("X-Intent", ""),
            "language": resp.headers.get("X-Language", language),
            "audio_data": audio_b64,
        }

    # ── Helper ─────────────────────────────────────────────
    async def _agent_call(self, path: str, language: str) -> dict:
        resp = await self._client.post(path, json={"language": language}, headers=self._headers())
        resp.raise_for_status()
        return resp.json()
