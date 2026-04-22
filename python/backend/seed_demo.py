"""
CREDA Demo Seed Script
======================
Seeds the creda_api database with two realistic demo users, complete with
profiles, portfolios (Indian MFs), goals, nudges, and conversation history.

Also creates matching Django auth users in creda_django via Django's ORM.

Usage:
    cd python/backend
    python seed_demo.py

Both databases must be running (make docker).
"""
import asyncio
import hashlib
import os
import secrets
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

# ── Add project paths ─────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════

def _uuid():
    return str(uuid.uuid4())


def _hash_pw(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${h.hex()}"


# ═══════════════════════════════════════════════════════════════════
#  Demo Data Definitions
# ═══════════════════════════════════════════════════════════════════

DEMO_PASSWORD = "demo1234"  # shared password for both demo users

# We'll assign integer-based IDs that match Django's auto-increment.
# Django User.id will be set explicitly. FastAPI user_id = str(django_id).
DEMO_USERS = [
    {
        "django_id": 100,  # Explicit Django user ID (avoids collision with real signups)
        "email": "rahul@demo.creda.in",
        "name": "Rahul Sharma",
        "profile": {
            "name": "Rahul Sharma",
            "age": 28,
            "city": "Bengaluru",
            "state": "Karnataka",
            "language": "en",
            "monthly_income": 150000,
            "monthly_expenses": 65000,
            "savings": 420000,
            "risk_appetite": "moderate",
            "employment_type": "salaried",
            "dependents": 0,
            "has_health_insurance": True,
            "life_insurance_cover": 5000000,
            "has_home_loan": False,
            "home_loan_outstanding": 0,
            "monthly_emi": 0,
            "emergency_fund": 350000,
            "epf_balance": 480000,
            "nps_balance": 120000,
            "ppf_balance": 200000,
            "investments_80c": 130000,
            "nps_contribution": 50000,
            "health_insurance_premium": 18000,
            "hra": 30000,
            "home_loan_interest": 0,
            "fire_target_age": 45,
            "fire_corpus_target": 50000000,
            "onboarding_complete": True,
        },
        "portfolio": {
            "total_invested": 1250000,
            "current_value": 1487500,
            "xirr": 14.8,
        },
        "funds": [
            {
                "fund_name": "Parag Parikh Flexi Cap Fund - Direct Growth",
                "amc": "PPFAS Mutual Fund",
                "scheme_type": "equity",
                "category": "flexi_cap",
                "plan_type": "direct",
                "invested": 300000,
                "current_value": 368000,
                "units": 4521.36,
                "xirr": 16.2,
                "expense_ratio": 0.63,
            },
            {
                "fund_name": "Mirae Asset Large Cap Fund - Direct Growth",
                "amc": "Mirae Asset Mutual Fund",
                "scheme_type": "equity",
                "category": "large_cap",
                "plan_type": "direct",
                "invested": 200000,
                "current_value": 234000,
                "units": 2156.78,
                "xirr": 13.5,
                "expense_ratio": 0.53,
            },
            {
                "fund_name": "Axis Small Cap Fund - Direct Growth",
                "amc": "Axis Mutual Fund",
                "scheme_type": "equity",
                "category": "small_cap",
                "plan_type": "direct",
                "invested": 150000,
                "current_value": 189000,
                "units": 1874.23,
                "xirr": 18.9,
                "expense_ratio": 0.49,
            },
            {
                "fund_name": "HDFC Mid-Cap Opportunities Fund - Direct Growth",
                "amc": "HDFC Mutual Fund",
                "scheme_type": "equity",
                "category": "mid_cap",
                "plan_type": "direct",
                "invested": 200000,
                "current_value": 241500,
                "units": 1432.67,
                "xirr": 15.7,
                "expense_ratio": 0.72,
            },
            {
                "fund_name": "SBI Equity Hybrid Fund - Direct Growth",
                "amc": "SBI Mutual Fund",
                "scheme_type": "hybrid",
                "category": "aggressive_hybrid",
                "plan_type": "direct",
                "invested": 150000,
                "current_value": 170000,
                "units": 756.89,
                "xirr": 11.2,
                "expense_ratio": 0.67,
            },
            {
                "fund_name": "ICICI Pru Nifty 50 Index Fund - Direct Growth",
                "amc": "ICICI Prudential Mutual Fund",
                "scheme_type": "equity",
                "category": "large_cap",
                "plan_type": "direct",
                "invested": 100000,
                "current_value": 115000,
                "units": 567.34,
                "xirr": 12.8,
                "expense_ratio": 0.18,
            },
            {
                "fund_name": "Kotak Corporate Bond Fund - Direct Growth",
                "amc": "Kotak Mutual Fund",
                "scheme_type": "debt",
                "category": "corporate_bond",
                "plan_type": "direct",
                "invested": 100000,
                "current_value": 110000,
                "units": 3245.12,
                "xirr": 7.8,
                "expense_ratio": 0.35,
            },
            {
                "fund_name": "Motilal Oswal Nasdaq 100 FOF - Direct Growth",
                "amc": "Motilal Oswal Mutual Fund",
                "scheme_type": "equity",
                "category": "international",
                "plan_type": "direct",
                "invested": 50000,
                "current_value": 60000,
                "units": 234.56,
                "xirr": 15.3,
                "expense_ratio": 0.48,
            },
        ],
        "goals": [
            {
                "goal_name": "Emergency Fund (6 months)",
                "target_amount": 400000,
                "target_date": date(2026, 12, 31),
                "monthly_investment": 10000,
                "current_saved": 350000,
                "recommended_sip": 5000,
                "expected_return_rate": 6.0,
                "is_on_track": True,
                "progress_pct": 87.5,
                "drift_amount": 0,
            },
            {
                "goal_name": "Europe Trip 2027",
                "target_amount": 500000,
                "target_date": date(2027, 6, 15),
                "monthly_investment": 25000,
                "current_saved": 180000,
                "recommended_sip": 23000,
                "expected_return_rate": 10.0,
                "is_on_track": True,
                "progress_pct": 36.0,
                "drift_amount": 12000,
            },
            {
                "goal_name": "Down Payment for Flat",
                "target_amount": 3000000,
                "target_date": date(2029, 3, 1),
                "monthly_investment": 50000,
                "current_saved": 750000,
                "recommended_sip": 55000,
                "expected_return_rate": 12.0,
                "is_on_track": False,
                "progress_pct": 25.0,
                "drift_amount": -180000,
            },
            {
                "goal_name": "FIRE Corpus",
                "target_amount": 50000000,
                "target_date": date(2043, 1, 1),
                "monthly_investment": 45000,
                "current_saved": 1487500,
                "recommended_sip": 48000,
                "expected_return_rate": 12.0,
                "is_on_track": True,
                "progress_pct": 3.0,
                "drift_amount": -25000,
            },
        ],
        "nudges": [
            {
                "nudge_type": "sip_reminder",
                "title": "SIP Due Tomorrow",
                "body": "Your monthly SIP of ₹45,000 across 5 funds is scheduled for tomorrow. Ensure sufficient balance in your bank account.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "rebalance_alert",
                "title": "Portfolio Rebalancing Needed",
                "body": "Your small-cap allocation has grown to 14% (target: 10%). Consider rebalancing by shifting ₹45,000 to large-cap or hybrid funds.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "tax_deadline",
                "title": "Tax-Saving Deadline Approaching",
                "body": "You've invested ₹1,30,000 of the ₹1,50,000 limit under Section 80C. Invest ₹20,000 more before March 31 to maximize your tax savings.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "goal_drift",
                "title": "Down Payment Goal Off Track",
                "body": "Your 'Down Payment for Flat' goal is ₹1,80,000 behind schedule. Consider increasing your SIP by ₹5,000/month to get back on track.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "expense_alert",
                "title": "Dining Expenses Up 35%",
                "body": "Your dining/food delivery spending is ₹12,500 this month vs ₹9,200 average. You're ₹3,300 over your usual spending.",
                "channel": "app",
                "is_read": True,
            },
        ],
        "conversations": [
            {"role": "user", "content": "What's my portfolio doing?", "intent": "portfolio_review"},
            {"role": "assistant", "content": "Your portfolio is worth ₹14,87,500 with an overall XIRR of 14.8%. Top performer: Axis Small Cap Fund at 18.9% XIRR. Your asset allocation looks healthy — 68% equity, 12% hybrid, 9% debt, 4% international, 7% EPF/PPF.", "agent_used": "portfolio_xray"},
            {"role": "user", "content": "Should I invest more in small caps?", "intent": "investment_advice"},
            {"role": "assistant", "content": "Your small-cap allocation is already at 14% — slightly above the typical 10% for a moderate risk profile. I'd suggest maintaining current SIPs rather than adding more. If you want higher growth, consider increasing your flexi-cap allocation (Parag Parikh) which gives you small-cap exposure with built-in rebalancing.", "agent_used": "portfolio_xray"},
        ],
    },
    {
        "django_id": 101,  # Second demo user
        "email": "priya@demo.creda.in",
        "name": "Priya Patel",
        "profile": {
            "name": "Priya Patel",
            "age": 35,
            "city": "Mumbai",
            "state": "Maharashtra",
            "language": "en",
            "monthly_income": 280000,
            "monthly_expenses": 130000,
            "savings": 1200000,
            "risk_appetite": "aggressive",
            "employment_type": "business",
            "dependents": 2,
            "has_health_insurance": True,
            "life_insurance_cover": 15000000,
            "has_home_loan": True,
            "home_loan_outstanding": 4500000,
            "monthly_emi": 42000,
            "emergency_fund": 800000,
            "epf_balance": 0,
            "nps_balance": 200000,
            "ppf_balance": 500000,
            "investments_80c": 150000,
            "nps_contribution": 50000,
            "health_insurance_premium": 35000,
            "hra": 0,
            "home_loan_interest": 380000,
            "fire_target_age": 50,
            "fire_corpus_target": 80000000,
            "onboarding_complete": True,
        },
        "portfolio": {
            "total_invested": 3800000,
            "current_value": 4750000,
            "xirr": 16.5,
        },
        "funds": [
            {
                "fund_name": "Quant Small Cap Fund - Direct Growth",
                "amc": "Quant Mutual Fund",
                "scheme_type": "equity",
                "category": "small_cap",
                "plan_type": "direct",
                "invested": 600000,
                "current_value": 840000,
                "units": 3245.67,
                "xirr": 24.1,
                "expense_ratio": 0.64,
            },
            {
                "fund_name": "Nippon India Small Cap Fund - Direct Growth",
                "amc": "Nippon India Mutual Fund",
                "scheme_type": "equity",
                "category": "small_cap",
                "plan_type": "direct",
                "invested": 500000,
                "current_value": 680000,
                "units": 4123.45,
                "xirr": 21.3,
                "expense_ratio": 0.62,
            },
            {
                "fund_name": "Parag Parikh Flexi Cap Fund - Direct Growth",
                "amc": "PPFAS Mutual Fund",
                "scheme_type": "equity",
                "category": "flexi_cap",
                "plan_type": "direct",
                "invested": 500000,
                "current_value": 620000,
                "units": 7623.45,
                "xirr": 16.8,
                "expense_ratio": 0.63,
            },
            {
                "fund_name": "HDFC Flexi Cap Fund - Direct Growth",
                "amc": "HDFC Mutual Fund",
                "scheme_type": "equity",
                "category": "flexi_cap",
                "plan_type": "direct",
                "invested": 400000,
                "current_value": 490000,
                "units": 2678.90,
                "xirr": 15.2,
                "expense_ratio": 0.77,
            },
            {
                "fund_name": "Axis ELSS Tax Saver Fund - Direct Growth",
                "amc": "Axis Mutual Fund",
                "scheme_type": "elss",
                "category": "elss",
                "plan_type": "direct",
                "invested": 300000,
                "current_value": 365000,
                "units": 3456.78,
                "xirr": 14.6,
                "expense_ratio": 0.55,
            },
            {
                "fund_name": "Mirae Asset Emerging Bluechip Fund - Direct Growth",
                "amc": "Mirae Asset Mutual Fund",
                "scheme_type": "equity",
                "category": "large_mid_cap",
                "plan_type": "direct",
                "invested": 400000,
                "current_value": 505000,
                "units": 5234.56,
                "xirr": 17.4,
                "expense_ratio": 0.58,
            },
            {
                "fund_name": "SBI Magnum Medium Duration Fund - Direct Growth",
                "amc": "SBI Mutual Fund",
                "scheme_type": "debt",
                "category": "medium_duration",
                "plan_type": "direct",
                "invested": 400000,
                "current_value": 430000,
                "units": 8765.43,
                "xirr": 7.2,
                "expense_ratio": 0.56,
            },
            {
                "fund_name": "ICICI Pru Technology Fund - Direct Growth",
                "amc": "ICICI Prudential Mutual Fund",
                "scheme_type": "equity",
                "category": "sectoral",
                "plan_type": "direct",
                "invested": 200000,
                "current_value": 265000,
                "units": 1234.56,
                "xirr": 19.8,
                "expense_ratio": 0.89,
            },
            {
                "fund_name": "Kotak Gilt Fund - Direct Growth",
                "amc": "Kotak Mutual Fund",
                "scheme_type": "debt",
                "category": "gilt",
                "plan_type": "direct",
                "invested": 300000,
                "current_value": 325000,
                "units": 4321.09,
                "xirr": 6.8,
                "expense_ratio": 0.42,
            },
            {
                "fund_name": "Motilal Oswal Nasdaq 100 FOF - Direct Growth",
                "amc": "Motilal Oswal Mutual Fund",
                "scheme_type": "equity",
                "category": "international",
                "plan_type": "direct",
                "invested": 200000,
                "current_value": 230000,
                "units": 934.56,
                "xirr": 12.5,
                "expense_ratio": 0.48,
            },
        ],
        "goals": [
            {
                "goal_name": "Children's Education Fund",
                "target_amount": 5000000,
                "target_date": date(2036, 6, 1),
                "monthly_investment": 25000,
                "current_saved": 850000,
                "recommended_sip": 22000,
                "expected_return_rate": 12.0,
                "is_on_track": True,
                "progress_pct": 17.0,
                "drift_amount": 45000,
            },
            {
                "goal_name": "Home Loan Prepayment",
                "target_amount": 2000000,
                "target_date": date(2028, 12, 31),
                "monthly_investment": 50000,
                "current_saved": 600000,
                "recommended_sip": 45000,
                "expected_return_rate": 8.0,
                "is_on_track": True,
                "progress_pct": 30.0,
                "drift_amount": 50000,
            },
            {
                "goal_name": "Business Expansion",
                "target_amount": 8000000,
                "target_date": date(2030, 1, 1),
                "monthly_investment": 80000,
                "current_saved": 1500000,
                "recommended_sip": 90000,
                "expected_return_rate": 14.0,
                "is_on_track": False,
                "progress_pct": 18.75,
                "drift_amount": -320000,
            },
            {
                "goal_name": "FIRE Corpus",
                "target_amount": 80000000,
                "target_date": date(2041, 1, 1),
                "monthly_investment": 100000,
                "current_saved": 4750000,
                "recommended_sip": 95000,
                "expected_return_rate": 13.0,
                "is_on_track": True,
                "progress_pct": 5.9,
                "drift_amount": 80000,
            },
        ],
        "nudges": [
            {
                "nudge_type": "rebalance_alert",
                "title": "High Small-Cap Concentration",
                "body": "Your small-cap allocation is 32% — well above the 15-20% range for even aggressive profiles. Consider booking partial profits and diversifying into large-cap or flexi-cap.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "tax_deadline",
                "title": "Section 80C Fully Utilized",
                "body": "Great news! You've maxed out your 80C deduction at ₹1,50,000. Consider NPS (80CCD) for an additional ₹50,000 deduction.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "home_loan",
                "title": "Home Loan Prepayment Opportunity",
                "body": "You have ₹6,00,000 saved towards home loan prepayment. Making a lump-sum prepayment now could save ₹3,40,000 in interest over the loan tenure.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "goal_drift",
                "title": "Business Expansion Goal Needs Attention",
                "body": "Your business expansion goal is ₹3,20,000 behind schedule. Consider increasing SIP by ₹10,000/month or extending the timeline by 6 months.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "market_insight",
                "title": "Sectoral Fund Outperformance",
                "body": "Your ICICI Pru Technology Fund returned 19.8% vs benchmark 14.2%. Consider taking some profits since sectoral concentration risk is elevated.",
                "channel": "app",
                "is_read": True,
            },
            {
                "nudge_type": "insurance_review",
                "title": "Annual Insurance Review",
                "body": "With 2 dependents and a home loan of ₹45L, your life cover of ₹1.5Cr looks adequate. However, consider increasing health insurance to ₹25L family floater.",
                "channel": "app",
                "is_read": True,
            },
        ],
        "conversations": [
            {"role": "user", "content": "My portfolio is too risky?", "intent": "risk_assessment"},
            {"role": "assistant", "content": "Yes, your small-cap allocation at 32% is high even for an aggressive profile. I'd recommend: (1) Stop new SIPs in small-cap funds, (2) Start a flexi-cap SIP of ₹30,000, (3) Gradually shift ₹3-4L from small-caps to large-cap/flexi-cap over 3-4 months via STP. This maintains growth potential while reducing volatility.", "agent_used": "portfolio_xray"},
            {"role": "user", "content": "How much tax can I save this year?", "intent": "tax"},
            {"role": "assistant", "content": "Great news — you're already doing well on tax saving! Here's your breakdown:\n• 80C: ₹1,50,000 (maxed via ELSS + PPF)\n• 80CCD(1B): ₹50,000 (NPS — fully utilized)\n• 80D: ₹35,000 (health insurance)\n• 24(b): ₹2,00,000 (home loan interest — of ₹3,80,000 paid)\nTotal deductions: ~₹4,35,000. Estimated tax saved: ~₹1,30,000. The only gap is the remaining ₹1,80,000 home loan interest you can't claim under 24(b) — consider Section 80EEA if applicable.", "agent_used": "tax_wizard"},
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════
#  Seed FastAPI Database (creda_api)
# ═══════════════════════════════════════════════════════════════════

async def seed_fastapi_db():
    """Seed the creda_api database with demo data."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.models import (
        Base, User, UserProfile, Portfolio, PortfolioFund,
        GoalPlan, Nudge, ConversationMessage, LifeEvent,
    )
    from app.config import settings

    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        for user_data in DEMO_USERS:
            user_id_str = str(user_data["django_id"])

            # Check if user already exists
            from sqlalchemy import select
            existing = await db.execute(select(User).where(User.email == user_data["email"]))
            if existing.scalar_one_or_none():
                print(f"  [skip] {user_data['email']} already exists in creda_api")
                continue

            # Create user (id = str(django_id) so headers match)
            user = User(
                id=user_id_str,
                email=user_data["email"],
                password_hash=_hash_pw(DEMO_PASSWORD),
                name=user_data["name"],
            )
            db.add(user)
            await db.flush()

            # Create profile
            prof_data = user_data["profile"]
            profile = UserProfile(user_id=user_id_str, **prof_data)
            db.add(profile)

            # Create portfolio + funds
            port_data = user_data["portfolio"]
            portfolio = Portfolio(
                user_id=user_id_str,
                total_invested=port_data["total_invested"],
                current_value=port_data["current_value"],
                xirr=port_data["xirr"],
                parsed_at=datetime.now(timezone.utc) - timedelta(days=2),
            )
            db.add(portfolio)
            await db.flush()

            for fund_data in user_data["funds"]:
                fund = PortfolioFund(portfolio_id=portfolio.id, **fund_data)
                db.add(fund)

            # Create goals
            for goal_data in user_data["goals"]:
                goal = GoalPlan(user_id=user_id_str, **goal_data)
                db.add(goal)

            # Create nudges
            now = datetime.now(timezone.utc)
            for i, nudge_data in enumerate(user_data["nudges"]):
                nudge = Nudge(
                    user_id=user_id_str,
                    sent_at=now - timedelta(hours=i * 6),
                    **nudge_data,
                )
                db.add(nudge)

            # Create conversation history
            session_id = _uuid()
            for j, msg in enumerate(user_data["conversations"]):
                conv = ConversationMessage(
                    user_id=user_id_str,
                    session_id=session_id,
                    role=msg["role"],
                    content=msg["content"],
                    intent=msg.get("intent", ""),
                    agent_used=msg.get("agent_used", ""),
                )
                db.add(conv)

            # Create a life event
            life_event = LifeEvent(
                user_id=user_id_str,
                event_type="job_change" if user_data["name"] == "Rahul Sharma" else "child",
                event_date=date(2025, 6, 1) if user_data["name"] == "Rahul Sharma" else date(2024, 3, 15),
                financial_impact=50000 if user_data["name"] == "Rahul Sharma" else -30000,
                notes="Joined new company with 40% hike" if user_data["name"] == "Rahul Sharma" else "Second child born — increased monthly expenses",
            )
            db.add(life_event)

            print(f"  [seed] {user_data['email']} — profile + {len(user_data['funds'])} funds + {len(user_data['goals'])} goals + {len(user_data['nudges'])} nudges")

        await db.commit()

    await engine.dispose()
    print("  FastAPI database (creda_api) seeded.")


# ═══════════════════════════════════════════════════════════════════
#  Seed Django Database (creda_django)
# ═══════════════════════════════════════════════════════════════════

def seed_django_db():
    """Seed the creda_django database with matching Django auth users."""
    # Setup Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "creda.settings")
    import django
    django.setup()

    from accounts.models import User as DjangoUser

    for user_data in DEMO_USERS:
        if DjangoUser.objects.filter(email=user_data["email"]).exists():
            print(f"  [skip] {user_data['email']} already exists in creda_django")
            continue

        user = DjangoUser(
            id=user_data["django_id"],
            username=user_data["email"],
            email=user_data["email"],
            first_name=user_data["name"].split()[0],
            last_name=" ".join(user_data["name"].split()[1:]),
        )
        user.set_password(DEMO_PASSWORD)
        user.save()
        print(f"  [seed] {user_data['email']} created in creda_django (id={user_data['django_id']})")

    print("  Django database (creda_django) seeded.")


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════

def main():
    print()
    print("=" * 60)
    print("  CREDA Demo Data Seeder")
    print("=" * 60)
    print()
    print(f"  Demo credentials:")
    print(f"    User 1: rahul@demo.creda.in / {DEMO_PASSWORD}")
    print(f"    User 2: priya@demo.creda.in / {DEMO_PASSWORD}")
    print()

    # 1. Seed Django database (synchronous)
    print("  [1/2] Seeding Django database (creda_django)...")
    seed_django_db()
    print()

    # 2. Seed FastAPI database (async)
    print("  [2/2] Seeding FastAPI database (creda_api)...")
    asyncio.run(seed_fastapi_db())
    print()

    print("=" * 60)
    print("  Done! Log in at http://localhost:8000 with:")
    print(f"    Email: rahul@demo.creda.in")
    print(f"    Password: {DEMO_PASSWORD}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
