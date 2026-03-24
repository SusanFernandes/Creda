"""
CREDA Finance Service — Database Models (SQLModel)
Provides persistence for user profiles, portfolios, conversations, and life events.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, unique=True)
    name: Optional[str] = None
    age: Optional[int] = None
    income: Optional[float] = None               # monthly, INR
    expenses: Optional[float] = None              # monthly, INR
    savings: Optional[float] = None               # total existing, INR
    dependents: Optional[int] = Field(default=0)
    risk_tolerance: Optional[int] = Field(default=3)  # 1-5
    goal_type: Optional[str] = Field(default="growth")
    time_horizon: Optional[int] = Field(default=10)   # years
    language: Optional[str] = Field(default="en")

    # Optional detailed fields
    monthly_emi: Optional[float] = Field(default=0)
    emergency_fund: Optional[float] = Field(default=0)
    life_insurance_cover: Optional[float] = Field(default=0)
    has_health_insurance: Optional[bool] = Field(default=False)
    investments_80c: Optional[float] = Field(default=0)    # Section 80C
    nps_contribution: Optional[float] = Field(default=0)   # 80CCD(1B)
    health_insurance_premium: Optional[float] = Field(default=0)  # 80D
    hra: Optional[float] = Field(default=0)
    home_loan_interest: Optional[float] = Field(default=0)
    target_retirement_age: Optional[int] = Field(default=60)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioSnapshot(SQLModel, table=True):
    __tablename__ = "portfolio_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    snapshot_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_invested: float = 0.0
    current_value: float = 0.0
    xirr: Optional[float] = None
    holdings_json: str = "{}"       # JSON string of holdings detail
    source: str = "manual"          # "cams_pdf" | "manual" | "aa"


class ConversationMessage(SQLModel, table=True):
    __tablename__ = "conversation_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    user_id: Optional[str] = None
    call_sid: Optional[str] = Field(default=None, index=True)  # Twilio voice call ID
    role: str                       # "user" | "assistant" | "system"
    content: str
    content_type: Optional[str] = Field(default="text")  # "text" | "voice_metadata"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LifeEvent(SQLModel, table=True):
    __tablename__ = "life_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    event_type: str                 # "baby" | "marriage" | "job_change" | etc.
    event_date: Optional[datetime] = None
    details_json: str = "{}"
    stress_result_json: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
