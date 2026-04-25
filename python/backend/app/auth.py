"""
Auth dependencies for CREDA FastAPI backend.

Modes:
1. Header passthrough (get_auth) — Django injects x-user-id, x-user-email headers
2. JWT bearer (get_current_user) — for WebSocket endpoints
3. Webhook secret (get_expense_webhook_or_user) — optional X-Webhook-Secret for POST /expenses
"""
import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


class AuthContext:
    __slots__ = ("user_id", "email")

    def __init__(self, user_id: str, email: str = ""):
        self.user_id = user_id
        self.email = email


def get_auth(request: Request) -> AuthContext:
    """Extract auth from headers injected by Django BackendClient."""
    user_id = (request.headers.get("x-user-id") or "").strip()
    email = (request.headers.get("x-user-email") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing x-user-id header")
    return AuthContext(user_id=user_id, email=email)


def _bearer_raw_token(request: Request) -> str:
    h = (request.headers.get("Authorization") or request.headers.get("authorization") or "").strip()
    if h.lower().startswith("bearer "):
        return h[7:].strip()
    return ""


def get_expense_webhook_or_user(request: Request) -> AuthContext:
    """
    For POST /expenses (in order):
    1. WHATSAPP_EXPENSE_TRUST_PUBLIC — no credentials; always WHATSAPP_EXPENSE_USER_ID (dev only).
    2. WHATSAPP_EXPENSE_WEBHOOK_SECRET — X-Webhook-Secret or Bearer token must match.
    3. Otherwise x-user-id (Django proxy) via get_auth.
    """
    webhook_uid = (settings.WHATSAPP_EXPENSE_USER_ID or "100").strip()
    if settings.WHATSAPP_EXPENSE_TRUST_PUBLIC:
        return AuthContext(user_id=webhook_uid, email="")

    secret = (settings.WHATSAPP_EXPENSE_WEBHOOK_SECRET or "").strip()
    if secret:
        provided = (
            (request.headers.get("X-Webhook-Secret") or request.headers.get("x-webhook-secret") or "")
            .strip()
        )
        if not provided:
            provided = _bearer_raw_token(request)
        if provided:
            if provided != secret:
                raise HTTPException(status_code=403, detail="Invalid webhook secret")
            return AuthContext(user_id=webhook_uid, email="")
    return get_auth(request)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AuthContext:
    """Validate JWT token — used by WebSocket and mobile endpoints."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing auth token")
    try:
        payload = pyjwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        return AuthContext(user_id=payload["user_id"], email=payload.get("email", ""))
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_jwt(user_id: str, email: str = "", expires_minutes: int = 60) -> str:
    """Create a JWT for a user — called by Django or the /auth/token endpoint."""
    import datetime
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=expires_minutes),
    }
    return pyjwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
