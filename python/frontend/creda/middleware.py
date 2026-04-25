"""
Middleware: BackendClient + async user resolution.
"""
import httpx
import jwt as pyjwt
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


def _fastapi_user_id_for_request(request) -> str | None:
    """UUID of the row in creda_api.users — session, else JWT claims, else None."""
    sid = request.session.get("backend_user_id")
    if sid:
        return str(sid)
    token = request.session.get("backend_jwt")
    if not token or not getattr(settings, "JWT_SECRET", None):
        return None
    try:
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        uid = payload.get("user_id")
        return str(uid) if uid else None
    except pyjwt.PyJWTError:
        return None


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
            # FastAPI users.id is a UUID; Django User.pk is an integer.
            backend_uid = _fastapi_user_id_for_request(self._request)
            headers["x-user-id"] = backend_uid if backend_uid else str(user.id)
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

    async def patch_profile(self, data: dict) -> dict:
        resp = await self._client.patch("/profile/upsert", json=data, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def get_assumptions(self) -> dict:
        resp = await self._client.get("/assumptions", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def patch_assumptions(self, data: dict) -> dict:
        resp = await self._client.patch("/assumptions", json=data, headers=self._headers())
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

    async def get_portfolio_summary_optional(self) -> dict | None:
        """Return None if user has no portfolio (404), else summary dict."""
        try:
            resp = await self._client.get("/portfolio/summary", headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    async def get_chat_history(self, limit: int = 20) -> list:
        resp = await self._client.get(
            "/chat/history", params={"limit": limit}, headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    async def run_xray(self) -> dict:
        resp = await self._client.post("/portfolio/xray", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def refresh_navs(self) -> dict:
        resp = await self._client.post("/portfolio/refresh-navs", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── Agents (direct endpoints) ──────────────────────────
    async def fire_planner(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/fire-planner", language)

    async def tax_wizard(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/tax-wizard", language)

    async def money_health(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/money-health", language)

    async def sip_calculator(
        self,
        goal_target_amount: float | None = None,
        goal_target_years: int | None = None,
        monthly_sip_available: float | None = None,
        language: str = "en",
    ) -> dict:
        payload: dict = {"language": language, "voice_mode": False}
        if goal_target_amount is not None:
            payload["goal_target_amount"] = goal_target_amount
        if goal_target_years is not None:
            payload["goal_target_years"] = goal_target_years
        if monthly_sip_available is not None:
            payload["monthly_sip_available"] = monthly_sip_available
        resp = await self._client.post("/agents/sip-calculator", json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def stress_test(
        self,
        events: list[str],
        language: str = "en",
        stress_scenario_params: dict | None = None,
    ) -> dict:
        payload: dict = {"events": events, "language": language}
        if stress_scenario_params is not None:
            payload["stress_scenario_params"] = stress_scenario_params
        resp = await self._client.post("/agents/stress-test", json=payload, headers=self._headers())
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

    # ── ET-Inspired Agents ─────────────────────────────────
    async def market_pulse(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/market-pulse", language)

    async def opportunity_radar(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/opportunity-radar", language)

    async def chart_pattern(
        self, symbol: str | None = None, timeframe: str = "3mo", language: str = "en",
    ) -> dict:
        payload: dict = {"language": language, "voice_mode": False, "timeframe": timeframe}
        if symbol:
            payload["symbol"] = symbol
        resp = await self._client.post("/agents/chart-pattern", json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

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

    async def expense_analytics(self, language: str = "en") -> dict:
        return await self._agent_call("/agents/expense-analytics", language)

    async def list_budget_expenses(self, month: str = "", limit: int = 100) -> list:
        params: dict[str, str | int] = {"limit": limit}
        if month:
            params["month"] = month
        resp = await self._client.get("/budget/expenses", params=params, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    async def post_budget_expense(
        self,
        category: str,
        amount: float,
        description: str = "",
        expense_date: str = "",
        payment_method: str = "upi",
        is_recurring: bool = False,
    ) -> dict:
        payload = {
            "category": category,
            "amount": amount,
            "description": description,
            "expense_date": expense_date,
            "payment_method": payment_method,
            "is_recurring": is_recurring,
        }
        resp = await self._client.post("/budget/expense", json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def delete_budget_expense(self, expense_id: str) -> dict:
        resp = await self._client.delete(f"/budget/expense/{expense_id}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── Nudges ─────────────────────────────────────────────
    async def generate_nudges(self) -> dict:
        resp = await self._client.post("/nudges/generate", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

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

    # ── Admin ──────────────────────────────────────────────
    async def admin_stats(self) -> dict:
        resp = await self._client.get("/admin/stats", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def admin_activity(self, limit: int = 50) -> list:
        resp = await self._client.get("/admin/activity", params={"limit": limit}, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def admin_users(self, limit: int = 50) -> list:
        resp = await self._client.get("/admin/users", params={"limit": limit}, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── Goal-Fund Linking ──────────────────────────────────
    async def goals_with_funds(self) -> dict:
        resp = await self._client.get("/portfolio/goals", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def create_goal(
        self,
        goal_name: str,
        target_amount: float,
        target_date: str | None = None,
        current_saved: float = 0,
        monthly_investment: float = 0,
    ) -> dict:
        payload: dict = {
            "goal_name": goal_name,
            "target_amount": target_amount,
            "current_saved": current_saved,
            "monthly_investment": monthly_investment,
        }
        if target_date:
            payload["target_date"] = target_date
        resp = await self._client.post("/portfolio/goals", json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def link_funds_to_goal(self, goal_id: str, fund_ids: list) -> dict:
        resp = await self._client.post("/portfolio/goals/link", json={
            "goal_id": goal_id, "fund_ids": fund_ids,
        }, headers=self._headers())
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

    async def life_event_advisor(self, message: str, language: str = "en") -> dict:
        resp = await self._client.post("/agents/life-event-advisor", json={
            "message": message, "language": language,
        }, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

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

    async def voice_navigate(self, audio_bytes: bytes, filename: str, language: str = "en") -> dict:
        """Send audio to voice navigate endpoint — returns intent + page URL + ack audio."""
        files = {"audio": (filename, audio_bytes, "audio/webm")}
        data = {"language": language}
        resp = await self._client.post("/voice/navigate", files=files, data=data, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── Helper ─────────────────────────────────────────────
    async def _agent_call(self, path: str, language: str) -> dict:
        resp = await self._client.post(path, json={"language": language}, headers=self._headers())
        resp.raise_for_status()
        return resp.json()


def _sync_backend_headers(request) -> dict[str, str]:
    """Same auth headers as BackendClient for sync HTTP (sidebar middleware)."""
    from django.contrib.auth.models import AnonymousUser

    user = getattr(request, "user", None)
    headers: dict[str, str] = {}
    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
        return headers
    backend_uid = _fastapi_user_id_for_request(request)
    headers["x-user-id"] = backend_uid if backend_uid else str(user.id)
    headers["x-user-email"] = getattr(user, "email", None) or ""
    jwt_token = request.session.get("backend_jwt")
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"
    return headers


def _fetch_sidebar_context(request):
    """Sync GET profile + pending nudge count for sidebar nav."""
    from django.conf import settings

    base = settings.BACKEND_API_URL.rstrip("/")
    h = _sync_backend_headers(request)
    if not h.get("x-user-id"):
        return None, 0
    try:
        with httpx.Client(timeout=4.0) as client:
            pr = client.get(f"{base}/profile/{h['x-user-id']}", headers=h)
            profile = pr.json() if pr.status_code == 200 else None
            nr = client.get(f"{base}/nudges/pending", headers=h)
            raw = nr.json() if nr.status_code == 200 else []
            nudges = raw if isinstance(raw, list) else []
            return profile, len(nudges)
    except Exception:
        return None, 0


def sidebar_context_middleware(get_response):
    """Attach sidebar_profile, nudge count, and global profile completeness for banners."""

    def middleware(request):
        request.sidebar_profile = None
        request.sidebar_nudge_count = 0
        request.profile_completeness_pct = 0.0
        request.profile_missing_fields = []
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            profile, ncount = _fetch_sidebar_context(request)
            request.sidebar_profile = profile
            request.sidebar_nudge_count = ncount
            if profile:
                try:
                    request.profile_completeness_pct = float(profile.get("completeness_pct") or 0)
                except (TypeError, ValueError):
                    request.profile_completeness_pct = 0.0
                raw = profile.get("missing_profile_fields")
                request.profile_missing_fields = raw if isinstance(raw, list) else []
        return get_response(request)

    return middleware
