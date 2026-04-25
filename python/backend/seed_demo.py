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
import socket
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

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


def _preflight_postgres() -> None:
    """Fail fast with a clear message if Postgres is not accepting connections."""
    endpoints: set[tuple[str, int]] = set()
    dj_host = os.environ.get("DJANGO_DB_HOST", "localhost")
    dj_port = int(os.environ.get("DJANGO_DB_PORT", "8010"))
    endpoints.add((dj_host, dj_port))

    try:
        from app.config import settings

        raw = settings.DATABASE_URL
        for dialect_prefix, plain in (
            ("postgresql+asyncpg://", "postgresql://"),
            ("postgres+asyncpg://", "postgresql://"),
        ):
            if raw.startswith(dialect_prefix):
                raw = plain + raw[len(dialect_prefix) :]
                break
        u = urlparse(raw)
        if u.hostname:
            endpoints.add((u.hostname, int(u.port or 5432)))
    except Exception:
        pass

    unreachable: list[tuple[str, int]] = []
    for host, port in endpoints:
        try:
            with socket.create_connection((host, port), timeout=2.0):
                pass
        except OSError:
            unreachable.append((host, port))

    if not unreachable:
        return

    lines = "\n".join(f"    {h}:{p}" for h, p in sorted(unreachable))
    print("  PostgreSQL is not accepting connections at:")
    print(lines)
    print()
    print("  Start the database first, for example:")
    print("    cd python && make docker")
    print("    (or from repo root: docker compose up -d postgres)")
    print()
    print("  Then retry: make seed")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
#  Demo Data Definitions
# ═══════════════════════════════════════════════════════════════════

DEMO_PASSWORD = "demo1234"  # shared password for both demo users

# ═══════════════════════════════════════════════════════════════════
#  ARJUN MEHTA + PRIYA — THE HACKATHON DEMO SCENARIO
#  Every number is calibrated to produce dramatic, specific outputs.
# ═══════════════════════════════════════════════════════════════════

DEMO_USERS = [
    # ── ARJUN MEHTA — Primary demo user ──────────────────────
    {
        "django_id": 100,
        "email": "arjun@demo.creda.in",
        "name": "Arjun Mehta",
        "profile": {
            "name": "Arjun Mehta",
            "age": 29,
            "city": "Bengaluru",
            "state": "Karnataka",
            "language": "en",
            "monthly_income": 180000,
            "monthly_expenses": 95000,   # rent 28k, food 12k, transport 8k, misc 47k
            "savings": 120000,
            "risk_appetite": "moderate",
            "employment_type": "salaried",
            "dependents": 0,
            "has_health_insurance": True,  # employer-provided 5L only
            "life_insurance_cover": 0,     # NO term life — critical gap
            "has_home_loan": False,
            "home_loan_outstanding": 0,
            "monthly_emi": 0,
            "emergency_fund": 60000,       # < 1 month expenses — critically low
            "epf_balance": 518400,         # 21,600/mo for ~2 years
            "nps_balance": 0,              # No NPS — gap
            "ppf_balance": 0,
            "investments_80c": 45000,      # only ELSS SIP so far — 1,05,000 remaining!
            "nps_contribution": 0,
            "health_insurance_premium": 0,  # employer pays, no personal 80D
            "hra": 28000,                  # rent in Bengaluru metro
            "home_loan_interest": 0,
            "fire_target_age": 50,
            "fire_corpus_target": 72000000,  # FIRE at 50
            "onboarding_complete": True,
        },
        "portfolio": {
            "total_invested": 730000,
            "current_value": 830500,
            "xirr": 13.2,  # deliberately below Nifty 50's 15.8%
        },
        "funds": [
            {
                "fund_name": "Mirae Asset Large Cap Fund - Direct Growth",
                "amc": "Mirae Asset Mutual Fund",
                "scheme_type": "equity",
                "category": "large_cap",
                "plan_type": "direct",
                "invested": 220000,
                "current_value": 268000,
                "units": 2467.89,
                "xirr": 12.1,
                "expense_ratio": 0.53,
            },
            {
                "fund_name": "Axis Midcap Fund - Direct Growth",
                "amc": "Axis Mutual Fund",
                "scheme_type": "equity",
                "category": "mid_cap",
                "plan_type": "direct",
                "invested": 150000,
                "current_value": 205000,
                "units": 1832.45,
                "xirr": 16.8,
                "expense_ratio": 0.46,
            },
            {
                "fund_name": "Parag Parikh Flexi Cap Fund - Direct Growth",
                "amc": "PPFAS Mutual Fund",
                "scheme_type": "equity",
                "category": "flexi_cap",
                "plan_type": "direct",
                "invested": 180000,
                "current_value": 231000,
                "units": 2841.23,
                "xirr": 14.3,
                "expense_ratio": 0.63,
            },
            {
                # Overlap problem: 2nd large cap, weak performer
                "fund_name": "ICICI Pru Bluechip Fund - Direct Growth",
                "amc": "ICICI Prudential Mutual Fund",
                "scheme_type": "equity",
                "category": "large_cap",
                "plan_type": "direct",
                "invested": 80000,
                "current_value": 94000,
                "units": 1234.56,
                "xirr": 8.9,
                "expense_ratio": 0.43,
            },
            {
                "fund_name": "SBI Small Cap Fund - Direct Growth",
                "amc": "SBI Mutual Fund",
                "scheme_type": "equity",
                "category": "small_cap",
                "plan_type": "direct",
                "invested": 60000,
                "current_value": 88000,
                "units": 987.65,
                "xirr": 21.4,
                "expense_ratio": 0.54,
            },
            {
                # Dead weight: 3rd large cap, worst performer, highest overlap
                "fund_name": "Axis Bluechip Fund - Direct Growth",
                "amc": "Axis Mutual Fund",
                "scheme_type": "equity",
                "category": "large_cap",
                "plan_type": "direct",
                "invested": 40000,
                "current_value": 44500,
                "units": 678.90,
                "xirr": 6.2,
                "expense_ratio": 0.32,
            },
        ],
        "goals": [
            {
                "goal_name": "Emergency Fund (6 months)",
                "target_amount": 570000,     # 95k × 6
                "target_date": date(2027, 6, 30),
                "monthly_investment": 5000,
                "current_saved": 60000,
                "recommended_sip": 42000,
                "expected_return_rate": 6.0,
                "is_on_track": False,
                "progress_pct": 10.5,        # dramatically low
                "drift_amount": -510000,
            },
            {
                "goal_name": "Wedding Fund",
                "target_amount": 800000,
                "target_date": date(2027, 1, 15),  # ~6 months away
                "monthly_investment": 15000,
                "current_saved": 120000,
                "recommended_sip": 115000,
                "expected_return_rate": 7.0,
                "is_on_track": False,
                "progress_pct": 15.0,
                "drift_amount": -680000,
            },
            {
                "goal_name": "Home Down Payment",
                "target_amount": 3000000,
                "target_date": date(2031, 6, 1),    # 5 years
                "monthly_investment": 0,
                "current_saved": 0,
                "recommended_sip": 38000,
                "expected_return_rate": 12.0,
                "is_on_track": False,
                "progress_pct": 0.0,
                "drift_amount": -3000000,
            },
            {
                "goal_name": "FIRE Corpus (Retire at 50)",
                "target_amount": 72000000,
                "target_date": date(2047, 6, 1),    # 21 years away
                "monthly_investment": 15000,
                "current_saved": 830500,
                "recommended_sip": 42000,
                "expected_return_rate": 12.0,
                "is_on_track": False,
                "progress_pct": 1.2,
                "drift_amount": -27000,
            },
        ],
        "nudges": [
            {
                "nudge_type": "sip_reminder",
                "title": "⚠️ SIP of ₹5,000 Due in 2 Days",
                "body": "Your monthly SIP of ₹5,000 in Axis Midcap is scheduled in 2 days. Ensure sufficient balance.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "emergency_alert",
                "title": "🚨 Emergency Fund: Only 10.5% of Target",
                "body": "Your emergency fund covers only ₹60,000 of your ₹5,70,000 target (6 months expenses). One medical emergency and you're liquidating SIPs.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "tax_deadline",
                "title": "💡 Tax Season: ₹1.05L of 80C Unused",
                "body": "You've invested only ₹45,000 of the ₹1,50,000 80C limit. Invest ₹55,000 in ELSS + ₹50,000 in NPS to save ₹32,760 in taxes. 47 days left.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "rebalance_alert",
                "title": "Portfolio Overlap: 78% in Large Cap",
                "body": "You hold 3 large-cap funds (Mirae, ICICI Bluechip, Axis Bluechip) with 78% overlap. Consider exiting Axis Bluechip (6.2% XIRR — worst performer).",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "insurance_alert",
                "title": "No Term Life Insurance",
                "body": "You have zero life insurance cover. With marriage in 6 months, get at least ₹1 crore term plan. Premium: ~₹800/month at age 29.",
                "channel": "app",
                "is_read": False,
            },
        ],

        "life_events": [
            {
                "event_type": "marriage",
                "event_date": date(2027, 1, 15),
                "financial_impact": -800000,
                "notes": "Marrying Priya in 6 months. Wedding budget ₹8L.",
            },
            {
                "event_type": "bonus",
                "event_date": date(2026, 4, 15),
                "financial_impact": 300000,
                "notes": "Performance bonus of ₹3,00,000 received.",
            },
        ],

        # Arjun's monthly budgets (current month)
        "budgets": [
            {"category": "Rent/Housing", "planned_amount": 28000, "actual_amount": 28000},
            {"category": "Groceries", "planned_amount": 12000, "actual_amount": 13500},
            {"category": "Transport", "planned_amount": 8000, "actual_amount": 7200},
            {"category": "Dining Out", "planned_amount": 6000, "actual_amount": 8500},
            {"category": "Utilities", "planned_amount": 4000, "actual_amount": 3800},
            {"category": "Shopping", "planned_amount": 5000, "actual_amount": 9200},
            {"category": "Entertainment", "planned_amount": 4000, "actual_amount": 5100},
            {"category": "Health & Fitness", "planned_amount": 3000, "actual_amount": 2800},
            {"category": "Subscriptions", "planned_amount": 2000, "actual_amount": 1899},
            {"category": "Miscellaneous", "planned_amount": 5000, "actual_amount": 4200},
        ],
        # Arjun's recent expenses (last 30 days)
        "expenses": [
            {"category": "Rent/Housing", "amount": 28000, "description": "April rent - Koramangala 2BHK", "days_ago": 1, "payment_method": "netbanking", "is_recurring": True},
            {"category": "Groceries", "amount": 3200, "description": "BigBasket weekly order", "days_ago": 2, "payment_method": "upi"},
            {"category": "Groceries", "amount": 2800, "description": "Zepto vegetables + fruits", "days_ago": 7, "payment_method": "upi"},
            {"category": "Groceries", "amount": 4500, "description": "Monthly staples - Amazon Fresh", "days_ago": 15, "payment_method": "card"},
            {"category": "Groceries", "amount": 3000, "description": "BigBasket weekly order", "days_ago": 22, "payment_method": "upi"},
            {"category": "Transport", "amount": 2400, "description": "Ola/Uber rides (weekly)", "days_ago": 3, "payment_method": "upi"},
            {"category": "Transport", "amount": 2100, "description": "Metro card recharge", "days_ago": 10, "payment_method": "upi"},
            {"category": "Transport", "amount": 2700, "description": "Ola rides + fuel", "days_ago": 20, "payment_method": "upi"},
            {"category": "Dining Out", "amount": 3200, "description": "Team dinner at Toit", "days_ago": 4, "payment_method": "card"},
            {"category": "Dining Out", "amount": 1800, "description": "Coffee + lunch meetings", "days_ago": 8, "payment_method": "upi"},
            {"category": "Dining Out", "amount": 2500, "description": "Weekend brunch - Café Azzure", "days_ago": 14, "payment_method": "card"},
            {"category": "Dining Out", "amount": 1000, "description": "Swiggy orders", "days_ago": 18, "payment_method": "upi"},
            {"category": "Utilities", "amount": 1800, "description": "BESCOM electricity bill", "days_ago": 5, "payment_method": "upi", "is_recurring": True},
            {"category": "Utilities", "amount": 1200, "description": "Internet + mobile recharge", "days_ago": 5, "payment_method": "upi", "is_recurring": True},
            {"category": "Utilities", "amount": 800, "description": "Water + maintenance", "days_ago": 5, "payment_method": "upi", "is_recurring": True},
            {"category": "Shopping", "amount": 4200, "description": "Myntra haul - wedding shopping", "days_ago": 6, "payment_method": "card"},
            {"category": "Shopping", "amount": 5000, "description": "Electronics - earbuds + charger", "days_ago": 12, "payment_method": "card"},
            {"category": "Entertainment", "amount": 1800, "description": "BookMyShow - movie + snacks", "days_ago": 9, "payment_method": "upi"},
            {"category": "Entertainment", "amount": 1500, "description": "Spotify + Netflix + Hotstar", "days_ago": 1, "payment_method": "card", "is_recurring": True},
            {"category": "Entertainment", "amount": 1800, "description": "Weekend trip to Nandi Hills", "days_ago": 16, "payment_method": "upi"},
            {"category": "Health & Fitness", "amount": 2800, "description": "Cult.fit gym membership", "days_ago": 1, "payment_method": "card", "is_recurring": True},
            {"category": "Subscriptions", "amount": 999, "description": "Swiggy One annual", "days_ago": 1, "payment_method": "card", "is_recurring": True},
            {"category": "Subscriptions", "amount": 900, "description": "ChatGPT + iCloud", "days_ago": 1, "payment_method": "card", "is_recurring": True},
            {"category": "Miscellaneous", "amount": 2000, "description": "Gift for friend's birthday", "days_ago": 11, "payment_method": "upi"},
            {"category": "Miscellaneous", "amount": 2200, "description": "Dry cleaning + laundry", "days_ago": 19, "payment_method": "cash"},
        ],
    },

    # ── PRIYA — Arjun's fiancée ──────────────────────────────
    {
        "django_id": 101,
        "email": "priya@demo.creda.in",
        "name": "Priya Sharma",
        "profile": {
            "name": "Priya Sharma",
            "age": 27,
            "city": "Bengaluru",
            "state": "Karnataka",
            "language": "en",
            "monthly_income": 140000,
            "monthly_expenses": 65000,
            "savings": 280000,
            "risk_appetite": "moderate",
            "employment_type": "salaried",  # Product Manager
            "dependents": 0,
            "has_health_insurance": True,
            "life_insurance_cover": 0,
            "has_home_loan": False,
            "home_loan_outstanding": 0,
            "monthly_emi": 0,
            "emergency_fund": 200000,
            "epf_balance": 336000,   # 16,800/mo for ~20 months
            "nps_balance": 0,
            "ppf_balance": 0,
            "investments_80c": 72000,
            "nps_contribution": 0,
            "health_insurance_premium": 0,
            "hra": 0,              # Lives with parents — cannot claim HRA
            "home_loan_interest": 0,
            "fire_target_age": 50,
            "fire_corpus_target": 50000000,
            "onboarding_complete": True,
        },
        "portfolio": {
            "total_invested": 320000,
            "current_value": 358000,
            "xirr": 11.5,
        },
        "funds": [
            {
                "fund_name": "UTI Nifty 50 Index Fund - Direct Growth",
                "amc": "UTI Mutual Fund",
                "scheme_type": "equity",
                "category": "large_cap",
                "plan_type": "direct",
                "invested": 200000,
                "current_value": 228000,
                "units": 1234.56,
                "xirr": 12.8,
                "expense_ratio": 0.18,
            },
            {
                "fund_name": "HDFC Corporate Bond Fund - Direct Growth",
                "amc": "HDFC Mutual Fund",
                "scheme_type": "debt",
                "category": "corporate_bond",
                "plan_type": "direct",
                "invested": 120000,
                "current_value": 130000,
                "units": 3456.78,
                "xirr": 7.8,
                "expense_ratio": 0.35,
            },
        ],
        "goals": [
            {
                "goal_name": "Wedding Contribution",
                "target_amount": 300000,
                "target_date": date(2027, 1, 15),
                "monthly_investment": 30000,
                "current_saved": 100000,
                "recommended_sip": 25000,
                "expected_return_rate": 7.0,
                "is_on_track": True,
                "progress_pct": 33.3,
                "drift_amount": 15000,
            },
            {
                "goal_name": "Career Growth Fund",
                "target_amount": 500000,
                "target_date": date(2028, 12, 31),
                "monthly_investment": 15000,
                "current_saved": 80000,
                "recommended_sip": 14000,
                "expected_return_rate": 10.0,
                "is_on_track": True,
                "progress_pct": 16.0,
                "drift_amount": 5000,
            },
        ],
        "nudges": [
            {
                "nudge_type": "tax_deadline",
                "title": "80C Gap: ₹78,000 Remaining",
                "body": "You've invested ₹72,000 of ₹1,50,000 under 80C. Invest ₹50,000 in NPS (80CCD) + ₹28,000 more in ELSS to save ₹24,180 in taxes.",
                "channel": "app",
                "is_read": False,
            },
            {
                "nudge_type": "insurance_alert",
                "title": "No Personal Health Insurance",
                "body": "You rely on employer health cover only. If you change jobs, you'll have no cover. Get a ₹5L personal plan — premium ~₹5,000/year at 27.",
                "channel": "app",
                "is_read": False,
            },
        ],

        # Priya — logged expenses + budgets (same pattern as Arjun; powers Expense Analytics)
        "budgets": [
            {"category": "Groceries", "planned_amount": 12000, "actual_amount": 11800},
            {"category": "Transport", "planned_amount": 7000, "actual_amount": 6400},
            {"category": "Dining Out", "planned_amount": 8000, "actual_amount": 7200},
            {"category": "Shopping", "planned_amount": 10000, "actual_amount": 8500},
            {"category": "Utilities", "planned_amount": 3000, "actual_amount": 2900},
            {"category": "Subscriptions", "planned_amount": 2500, "actual_amount": 2499},
            {"category": "Miscellaneous", "planned_amount": 4000, "actual_amount": 3600},
        ],
        "expenses": [
            {"category": "Groceries", "amount": 4200, "description": "BigBasket + local market", "days_ago": 2, "payment_method": "upi"},
            {"category": "Groceries", "amount": 3800, "description": "Weekly stock-up", "days_ago": 9, "payment_method": "upi"},
            {"category": "Transport", "amount": 2200, "description": "Metro + Uber", "days_ago": 3, "payment_method": "upi"},
            {"category": "Transport", "amount": 2100, "description": "Cab to office", "days_ago": 11, "payment_method": "upi"},
            {"category": "Dining Out", "amount": 2800, "description": "Dinner with team", "days_ago": 4, "payment_method": "card"},
            {"category": "Dining Out", "amount": 1600, "description": "Cafe weekend", "days_ago": 14, "payment_method": "upi"},
            {"category": "Shopping", "amount": 4500, "description": "Wedding outfit prep", "days_ago": 6, "payment_method": "card"},
            {"category": "Utilities", "amount": 1200, "description": "Mobile + broadband", "days_ago": 1, "payment_method": "upi", "is_recurring": True},
            {"category": "Utilities", "amount": 900, "description": "Electric share at parents", "days_ago": 5, "payment_method": "upi"},
            {"category": "Subscriptions", "amount": 999, "description": "Streaming bundle", "days_ago": 1, "payment_method": "card", "is_recurring": True},
            {"category": "Subscriptions", "amount": 800, "description": "Notion + tools", "days_ago": 1, "payment_method": "card", "is_recurring": True},
            {"category": "Miscellaneous", "amount": 2000, "description": "Gifts", "days_ago": 12, "payment_method": "upi"},
        ],

        "life_events": [
            {
                "event_type": "marriage",
                "event_date": date(2027, 1, 15),
                "financial_impact": -300000,
                "notes": "Marrying Arjun. Contributing ₹3L to wedding.",
            },
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════
#  Seed FastAPI Database (creda_api)
# ═══════════════════════════════════════════════════════════════════
DEMO_EMAILS = {u["email"] for u in DEMO_USERS}


async def seed_fastapi_db():
    """Seed the creda_api database with demo data."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.models import (
        Base, User, UserProfile, Portfolio, PortfolioFund,
        GoalPlan, Nudge, ConversationMessage, LifeEvent, FamilyLink,
        Budget, Expense,
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

            # Check if user already exists (by id or email)
            from sqlalchemy import select
            existing = await db.execute(
                select(User).where((User.id == user_id_str) | (User.email == user_data["email"]))
            )
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

            # Create life events
            for evt in user_data.get("life_events", []):
                life_event = LifeEvent(
                    user_id=user_id_str,
                    event_type=evt["event_type"],
                    event_date=evt["event_date"],
                    financial_impact=evt["financial_impact"],
                    notes=evt.get("notes", ""),
                )
                db.add(life_event)

            # Create budgets (current month)
            current_month = datetime.now().strftime("%Y-%m")
            for bud in user_data.get("budgets", []):
                budget = Budget(
                    user_id=user_id_str,
                    month=current_month,
                    category=bud["category"],
                    planned_amount=bud["planned_amount"],
                    actual_amount=bud["actual_amount"],
                )
                db.add(budget)

            # Create expenses (recent)
            today = date.today()
            for exp in user_data.get("expenses", []):
                expense = Expense(
                    user_id=user_id_str,
                    category=exp["category"],
                    amount=exp["amount"],
                    description=exp.get("description", ""),
                    expense_date=today - timedelta(days=exp.get("days_ago", 0)),
                    payment_method=exp.get("payment_method", "upi"),
                    is_recurring=exp.get("is_recurring", False),
                )
                db.add(expense)

            n_bud = len(user_data.get("budgets", []))
            n_exp = len(user_data.get("expenses", []))
            print(f"  [seed] {user_data['email']} — profile + {len(user_data['funds'])} funds + {len(user_data['goals'])} goals + {len(user_data['nudges'])} nudges + {n_bud} budgets + {n_exp} expenses")

        # Link Arjun and Priya as spouse pair
        arjun_id = str(DEMO_USERS[0]["django_id"])
        priya_id = str(DEMO_USERS[1]["django_id"])
        existing_link = await db.execute(
            select(FamilyLink).where(
                FamilyLink.owner_id == arjun_id,
                FamilyLink.member_id == priya_id,
            )
        )
        if not existing_link.scalar_one_or_none():
            link = FamilyLink(
                owner_id=arjun_id,
                member_id=priya_id,
                relationship_type="spouse",
                is_accepted=True,
            )
            db.add(link)
            print(f"  [seed] Family link: Arjun ↔ Priya (spouse)")

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
        ex = DjangoUser.objects.filter(email=user_data["email"]).first()
        if ex:
            ex.set_password(DEMO_PASSWORD)
            ex.save()
            print(f"  [sync] {user_data['email']} — creda_django password resynced to demo value")
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
    print(f"    User 1: arjun@demo.creda.in / {DEMO_PASSWORD}")
    print(f"    User 2: priya@demo.creda.in / {DEMO_PASSWORD}")
    print()

    _preflight_postgres()

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
    print(f"    Email: arjun@demo.creda.in")
    print(f"    Password: {DEMO_PASSWORD}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
