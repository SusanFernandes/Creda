"""Auth router — token generation, user registration, rate-limited."""
import hashlib
import logging
import secrets
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_jwt
from app.config import settings
from app.database import get_db
from app.models import User

logger = logging.getLogger("creda.auth")
router = APIRouter()

# Simple in-memory rate limiter (per-IP, per-minute)
_rate_limits: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key: str, max_requests: int, window: int = 60):
    """Raise 429 if rate limit exceeded."""
    now = time.time()
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < window]
    if len(_rate_limits[key]) >= max_requests:
        raise HTTPException(429, "Too many requests. Please try again later.")
    _rate_limits[key].append(now)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user_id: str


def _hash_pw(password: str, salt: str = "") -> str:
    if not salt:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${h.hex()}"


def _verify_pw(password: str, stored: str) -> bool:
    salt, hashed = stored.split("$", 1)
    return _hash_pw(password, salt).split("$", 1)[1] == hashed


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(f"register:{request.client.host}", settings.RATE_LIMIT_REGISTER)
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    user = User(email=req.email, password_hash=_hash_pw(req.password), name=req.name)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_jwt(user.id, user.email)
    return TokenResponse(token=token, user_id=user.id)


@router.post("/token", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(f"login:{request.client.host}", settings.RATE_LIMIT_LOGIN)
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not _verify_pw(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = create_jwt(user.id, user.email)
    return TokenResponse(token=token, user_id=user.id)
