"""
Auth dependencies for CREDA FastAPI backend.

Two modes:
1. Header passthrough (get_auth) — Django injects x-user-id, x-user-email headers
2. JWT bearer (get_current_user) — for WebSocket endpoints
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
