"""Auth router — token generation, user registration, password reset, rate-limited."""
import hashlib
import logging
import secrets
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_jwt, AuthContext, get_auth
from app.config import settings
from app.database import get_db
from app.models import User

logger = logging.getLogger("creda.auth")
router = APIRouter()

# Simple in-memory rate limiter (per-IP, per-minute)
_rate_limits: dict[str, list[float]] = defaultdict(list)

# Password reset tokens: token -> (user_id, expires_at)
_reset_tokens: dict[str, tuple[str, float]] = {}
_RESET_TOKEN_EXPIRY = 3600  # 1 hour


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


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


@router.post("/password-reset-request")
async def password_reset_request(
    req: PasswordResetRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Generate a password reset token. In production, this sends an email."""
    _check_rate_limit(f"reset:{request.client.host}", 3)

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If an account exists with that email, a reset link has been sent."}

    # Generate secure token
    token = secrets.token_urlsafe(48)
    _reset_tokens[token] = (user.id, time.time() + _RESET_TOKEN_EXPIRY)

    # Clean expired tokens
    now = time.time()
    expired = [t for t, (_, exp) in _reset_tokens.items() if exp < now]
    for t in expired:
        _reset_tokens.pop(t, None)

    logger.info("Password reset token generated for user %s (token: %s...)", user.email, token[:8])

    return {
        "message": "If an account exists with that email, a reset link has been sent.",
        "reset_token": token,  # Remove in production — only for dev/testing
    }


@router.post("/password-reset-confirm")
async def password_reset_confirm(
    req: PasswordResetConfirm, request: Request, db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with token."""
    _check_rate_limit(f"reset-confirm:{request.client.host}", 5)

    entry = _reset_tokens.get(req.token)
    if not entry:
        raise HTTPException(400, "Invalid or expired reset token")

    user_id, expires_at = entry
    if time.time() > expires_at:
        _reset_tokens.pop(req.token, None)
        raise HTTPException(400, "Reset token has expired")

    if len(req.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, "User not found")

    user.password_hash = _hash_pw(req.new_password)
    await db.commit()

    _reset_tokens.pop(req.token, None)

    logger.info("Password reset completed for user %s", user.email)
    return {"message": "Password has been reset successfully. You can now log in."}


# ═══════════════════════════════════════════════════════════════════════════
#  EMAIL VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

class EmailVerifyRequest(BaseModel):
    token: str


@router.post("/send-verification")
async def send_verification(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Generate email verification token. In production, sends email."""
    from app.models import EmailVerification
    from datetime import datetime, timedelta

    _check_rate_limit(f"verify:{request.client.host}", 3)

    # Check if already verified
    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.user_id == auth.user_id,
            EmailVerification.verified == True,  # noqa: E712
        )
    )
    if result.scalars().first():
        return {"message": "Email already verified", "verified": True}

    # Generate token
    token = secrets.token_urlsafe(32)
    verification = EmailVerification(
        user_id=auth.user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(verification)
    await db.commit()

    logger.info("Verification token generated for user %s", auth.user_id)

    return {
        "message": "Verification email sent (check console in dev mode)",
        "verification_token": token,  # Remove in production
    }


@router.post("/verify-email")
async def verify_email(
    req: EmailVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify email with token."""
    from app.models import EmailVerification
    from datetime import datetime

    result = await db.execute(
        select(EmailVerification).where(EmailVerification.token == req.token)
    )
    verification = result.scalars().first()

    if not verification:
        raise HTTPException(400, "Invalid verification token")

    if verification.verified:
        return {"message": "Email already verified", "verified": True}

    if datetime.utcnow() > verification.expires_at:
        raise HTTPException(400, "Verification token has expired. Request a new one.")

    verification.verified = True
    await db.commit()

    logger.info("Email verified for user %s", verification.user_id)
    return {"message": "Email verified successfully!", "verified": True}


@router.get("/verification-status")
async def verification_status(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Check if user's email is verified."""
    from app.models import EmailVerification

    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.user_id == auth.user_id,
            EmailVerification.verified == True,  # noqa: E712
        )
    )
    return {"verified": result.scalars().first() is not None}
