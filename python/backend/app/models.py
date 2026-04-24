"""
All PostgreSQL models for CREDA.

Tables: users, user_profiles, portfolios, portfolio_funds,
        conversation_messages, life_events, nudges, goal_plans,
        whatsapp_sessions, advice_logs, family_links
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text,
    func, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    portfolios = relationship("Portfolio", back_populates="user")
    conversations = relationship("ConversationMessage", back_populates="user")
    nudges = relationship("Nudge", back_populates="user")
    goals = relationship("GoalPlan", back_populates="user")


# ═══════════════════════════════════════════════════════════════════════════
#  USER PROFILES
# ═══════════════════════════════════════════════════════════════════════════

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    name = Column(String(255), default="")
    age = Column(Integer, default=30)
    city = Column(String(100), default="")
    state = Column(String(100), default="")
    language = Column(String(10), default="en")  # BCP-47: hi, ta, te, mr, bn, kn, ...
    monthly_income = Column(Float, default=0)
    monthly_expenses = Column(Float, default=0)
    savings = Column(Float, default=0)
    risk_appetite = Column(String(20), default="moderate")  # conservative | moderate | aggressive
    employment_type = Column(String(30), default="salaried")  # salaried | self-employed | business
    dependents = Column(Integer, default=0)
    # ── Insurance ──
    has_health_insurance = Column(Boolean, default=False)
    life_insurance_cover = Column(Float, default=0)
    # ── Loans ──
    has_home_loan = Column(Boolean, default=False)
    home_loan_outstanding = Column(Float, default=0)
    monthly_emi = Column(Float, default=0)
    # ── Investments ──
    emergency_fund = Column(Float, default=0)
    epf_balance = Column(Float, default=0)
    nps_balance = Column(Float, default=0)
    ppf_balance = Column(Float, default=0)
    investments_80c = Column(Float, default=0)
    nps_contribution = Column(Float, default=0)
    health_insurance_premium = Column(Float, default=0)
    hra = Column(Float, default=0)
    home_loan_interest = Column(Float, default=0)
    # ── FIRE ──
    fire_target_age = Column(Integer, default=55)
    fire_corpus_target = Column(Float, default=0)
    # ── Onboarding ──
    onboarding_complete = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


# ═══════════════════════════════════════════════════════════════════════════
#  PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_invested = Column(Float, default=0)
    current_value = Column(Float, default=0)
    xirr = Column(Float, default=0)
    parsed_at = Column(DateTime, nullable=True)
    last_xray_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="portfolios")
    funds = relationship("PortfolioFund", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioFund(Base):
    __tablename__ = "portfolio_funds"

    id = Column(String, primary_key=True, default=_uuid)
    portfolio_id = Column(String, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    fund_name = Column(String(300), nullable=False)
    amc = Column(String(200), default="")
    scheme_type = Column(String(50), default="")         # equity | debt | hybrid | elss
    category = Column(String(50), default="")             # large_cap | mid_cap | small_cap
    plan_type = Column(String(20), default="")            # regular | direct
    invested = Column(Float, default=0)
    current_value = Column(Float, default=0)
    units = Column(Float, default=0)
    xirr = Column(Float, default=0)
    benchmark = Column(String(50), default="")
    alpha_vs_benchmark = Column(Float, default=0)
    overlap_score = Column(Float, default=0)
    expense_ratio = Column(Float, default=0)

    portfolio = relationship("Portfolio", back_populates="funds")


# ═══════════════════════════════════════════════════════════════════════════
#  CONVERSATIONS
# ═══════════════════════════════════════════════════════════════════════════

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)             # user | assistant
    content = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    intent = Column(String(50), default="")
    agent_used = Column(String(50), default="")
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="conversations")


# ═══════════════════════════════════════════════════════════════════════════
#  LIFE EVENTS
# ═══════════════════════════════════════════════════════════════════════════

class LifeEvent(Base):
    __tablename__ = "life_events"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)       # marriage | child | job_change | ...
    event_date = Column(Date, nullable=True)
    financial_impact = Column(Float, default=0)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════
#  NUDGES (proactive notifications)
# ═══════════════════════════════════════════════════════════════════════════

class Nudge(Base):
    __tablename__ = "nudges"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nudge_type = Column(String(50), nullable=False)       # sip_reminder | tax_deadline | rebalance_alert | ...
    title = Column(String(300), default="")
    body = Column(Text, default="")
    channel = Column(String(20), default="app")           # app | whatsapp | email
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, server_default=func.now())
    action_url = Column(String(500), default="")

    user = relationship("User", back_populates="nudges")


# ═══════════════════════════════════════════════════════════════════════════
#  GOAL PLANS
# ═══════════════════════════════════════════════════════════════════════════

class GoalPlan(Base):
    __tablename__ = "goal_plans"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal_name = Column(String(200), nullable=False)
    target_amount = Column(Float, default=0)
    target_date = Column(Date, nullable=True)
    monthly_investment = Column(Float, default=0)
    current_saved = Column(Float, default=0)
    recommended_sip = Column(Float, default=0)
    expected_return_rate = Column(Float, default=12.0)
    is_on_track = Column(Boolean, default=True)
    # Goal-linked portfolio (fund IDs tagged to this goal)
    linked_fund_ids = Column(JSON, default=list)
    drift_amount = Column(Float, default=0)           # +ve = overfunded, -ve = underfunded
    progress_pct = Column(Float, default=0)            # 0-100
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="goals")


# ═══════════════════════════════════════════════════════════════════════════
#  WHATSAPP SESSIONS
# ═══════════════════════════════════════════════════════════════════════════

class WhatsAppSession(Base):
    __tablename__ = "whatsapp_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    phone_number = Column(String(20), unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    language = Column(String(10), default="hi")
    is_verified = Column(Boolean, default=False)
    last_message_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════
#  SEBI COMPLIANCE — ADVICE AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════

class AdviceLog(Base):
    """
    SEBI RIA compliance: timestamped record of every AI recommendation.
    Stores the prompt, model, response, user context, and suitability rationale.
    """
    __tablename__ = "advice_logs"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(100), default="")
    # What triggered the advice
    intent = Column(String(50), nullable=False)
    agent_used = Column(String(50), nullable=False)
    user_message = Column(Text, default="")
    # Model details
    model_name = Column(String(100), default="llama-3.3-70b-versatile")
    model_version = Column(String(50), default="")
    # Full response
    response_text = Column(Text, default="")
    agent_output = Column(JSON, default=dict)       # raw structured output
    # User context at time of advice
    risk_profile = Column(String(20), default="")
    age_at_advice = Column(Integer, default=0)
    income_at_advice = Column(Float, default=0)
    portfolio_value_at_advice = Column(Float, default=0)
    # Suitability
    suitability_rationale = Column(Text, default="")  # auto-generated
    is_suitable = Column(Boolean, default=True)
    # Metadata
    language = Column(String(10), default="en")
    channel = Column(String(20), default="web")       # web | whatsapp | voice
    response_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════
#  FAMILY LINKS — HOUSEHOLD WEALTH VIEW
# ═══════════════════════════════════════════════════════════════════════════

class FamilyLink(Base):
    """Link family members for household net worth aggregation."""
    __tablename__ = "family_links"

    id = Column(String, primary_key=True, default=_uuid)
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(30), default="spouse")  # spouse | parent | child | sibling
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════
#  BUDGETS — MONTHLY BUDGET TRACKING
# ═══════════════════════════════════════════════════════════════════════════

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    month = Column(String(7), nullable=False)             # "2025-01"
    category = Column(String(100), nullable=False)        # food | transport | rent | ...
    planned_amount = Column(Float, default=0)
    actual_amount = Column(Float, default=0)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(500), default="")
    expense_date = Column(Date, nullable=False)
    payment_method = Column(String(50), default="")       # upi | card | cash | netbanking
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════
#  ACTIVITY LOG — USER ACTION AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)          # login | portfolio_upload | chat | voice_query | ...
    detail = Column(Text, default="")
    ip_address = Column(String(45), default="")
    user_agent = Column(String(500), default="")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════
#  EMAIL VERIFICATION TOKENS
# ═══════════════════════════════════════════════════════════════════════════

class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(200), unique=True, nullable=False)
    verified = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
