"""
Nudge worker — proactive financial notifications via APScheduler.
Runs periodic checks and generates nudges for users.
"""
import logging
from datetime import datetime, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import UserProfile, Nudge

logger = logging.getLogger("creda.nudge_worker")


async def run_nudge_checks():
    """Run all nudge checks for all users. Called by APScheduler."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserProfile).where(UserProfile.onboarding_complete == True))
        profiles = result.scalars().all()

        for profile in profiles:
            try:
                await _check_sip_reminder(profile, db)
                await _check_emergency_fund(profile, db)
                await _check_insurance_gap(profile, db)
                await _check_tax_deadline(profile, db)
                await _check_goal_drift(profile, db)
                await _check_loss_aversion(profile, db)
                await _check_advance_tax(profile, db)
            except Exception as e:
                logger.error("Nudge check failed for user %s: %s", profile.user_id, e)

        await db.commit()


async def _check_sip_reminder(profile: UserProfile, db: AsyncSession):
    """Remind users about SIP at start of month."""
    today = date.today()
    if today.day not in (1, 2):
        return

    income = profile.monthly_income or 0
    expenses = profile.monthly_expenses or 0
    savings = income - expenses

    if savings > 0:
        await _create_nudge(
            db, profile.user_id, "sip_reminder",
            "SIP Reminder 📊",
            f"It's the start of the month! Make sure your SIPs of ₹{savings:,.0f} are on track.",
            "/dashboard",
        )


async def _check_emergency_fund(profile: UserProfile, db: AsyncSession):
    """Alert if emergency fund is below 3 months expenses."""
    expenses = profile.monthly_expenses or 0
    emergency = profile.emergency_fund or 0

    if expenses > 0 and emergency < expenses * 3:
        months = emergency / expenses if expenses > 0 else 0
        await _create_nudge(
            db, profile.user_id, "emergency_fund_low",
            "Emergency Fund Alert ⚠️",
            f"Your emergency fund covers only {months:.1f} months. Target: 6 months (₹{expenses * 6:,.0f}).",
            "/health",
        )


async def _check_insurance_gap(profile: UserProfile, db: AsyncSession):
    """Check if user needs life/health insurance."""
    if not profile.has_health_insurance:
        await _create_nudge(
            db, profile.user_id, "insurance_gap",
            "Health Insurance Needed 🏥",
            "You don't have health insurance. A ₹5L family floater costs ~₹8,000-15,000/year and saves ₹25,000 in 80D tax.",
            "/health",
        )


async def _check_tax_deadline(profile: UserProfile, db: AsyncSession):
    """Remind about key tax deadlines."""
    today = date.today()
    # March end — 80C investments deadline
    if today.month == 3 and today.day >= 15:
        investments_80c = profile.investments_80c or 0
        if investments_80c < 150000:
            gap = 150000 - investments_80c
            await _create_nudge(
                db, profile.user_id, "tax_deadline",
                "Tax Saving Deadline! 🏷️",
                f"March 31 deadline approaching! ₹{gap:,.0f} unused under 80C. Consider ELSS, PPF, or NPS.",
                "/tax",
            )


async def _check_goal_drift(profile: UserProfile, db: AsyncSession):
    """Alert if any goal is drifting off-track (progress < 80% of expected)."""
    from app.models import GoalPlan
    result = await db.execute(
        select(GoalPlan).where(GoalPlan.user_id == profile.user_id)
    )
    goals = result.scalars().all()

    for goal in goals:
        if not goal.target_amount or not goal.target_date or not goal.monthly_sip:
            continue
        months_total = max(
            (goal.target_date.year - goal.created_at.year) * 12
            + (goal.target_date.month - goal.created_at.month), 1
        )
        months_elapsed = max(
            (date.today().year - goal.created_at.year) * 12
            + (date.today().month - goal.created_at.month), 0
        )
        expected = goal.monthly_sip * months_elapsed
        actual = goal.progress_pct * goal.target_amount / 100 if goal.progress_pct else 0

        if expected > 0 and actual < expected * 0.8:
            shortfall = expected - actual
            await _create_nudge(
                db, profile.user_id, f"goal_drift_{goal.id}",
                f"Goal Drift: {goal.goal_name} 📉",
                f"Your '{goal.goal_name}' is ₹{shortfall:,.0f} behind schedule. "
                f"Consider increasing SIP by ₹{shortfall / max(months_total - months_elapsed, 1):,.0f}/month.",
                "/goals",
            )


async def _check_loss_aversion(profile: UserProfile, db: AsyncSession):
    """Behavioral nudge: detect panic patterns and encourage steady investing."""
    from app.models import Holding
    result = await db.execute(
        select(Holding).where(Holding.user_id == profile.user_id)
    )
    holdings = result.scalars().all()
    if not holdings:
        return

    total_invested = sum(h.buy_price * h.quantity for h in holdings if h.buy_price and h.quantity)
    total_current = sum(h.current_price * h.quantity for h in holdings if h.current_price and h.quantity)

    if total_invested > 0:
        portfolio_return = (total_current - total_invested) / total_invested * 100
        if portfolio_return < -5:
            await _create_nudge(
                db, profile.user_id, "loss_aversion",
                "Market Dip — Stay the Course 🧘",
                f"Your portfolio is down {abs(portfolio_return):.1f}%. "
                "Historical data shows markets recover within 12-18 months. "
                "Avoid panic selling — consider adding to SIPs during dips.",
                "/portfolio",
            )
        elif portfolio_return > 20:
            await _create_nudge(
                db, profile.user_id, "profit_booking",
                "Time to Rebalance? 📊",
                f"Your portfolio is up {portfolio_return:.1f}%. "
                "Consider booking partial profits and rebalancing to your target allocation.",
                "/portfolio",
            )


async def _check_advance_tax(profile: UserProfile, db: AsyncSession):
    """Remind about advance tax quarterly deadlines."""
    today = date.today()
    income = (profile.monthly_income or 0) * 12
    if income < 1000000:
        return  # Only relevant for 10L+ earners

    deadlines = {6: (15, "Q1 — 15%"), 9: (15, "Q2 — 45%"), 12: (15, "Q3 — 75%"), 3: (15, "Q4 — 100%")}
    if today.month in deadlines:
        day, label = deadlines[today.month]
        if today.day <= day:
            est_tax = max(income * 0.20 - 125000, 0) * 1.04  # Rough estimate
            await _create_nudge(
                db, profile.user_id, "advance_tax",
                f"Advance Tax Due: {label} 🏦",
                f"Advance tax installment due by {today.month}/{day}. "
                f"Estimated annual liability: ₹{est_tax:,.0f}. File via TIN-NSDL portal.",
                "/tax",
            )


async def run_premarket_briefing():
    """Generate pre-market briefing nudge for all users. Scheduled at 9:15 AM IST."""
    from app.agents.market_pulse import _fetch_indices, _fetch_headlines, _score_sentiment, _generate_premarket_briefing

    try:
        indices = await _fetch_indices()
        headlines = await _fetch_headlines()
        sentiment = await _score_sentiment(headlines)
        briefing = await _generate_premarket_briefing(indices, headlines, sentiment, {})
    except Exception as e:
        logger.error("Pre-market briefing generation failed: %s", e)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserProfile).where(UserProfile.onboarding_complete == True))
        profiles = result.scalars().all()

        for profile in profiles:
            try:
                await _create_nudge(
                    db, profile.user_id, "premarket_briefing",
                    "Morning Market Briefing ☀️",
                    briefing,
                    "/market",
                )
            except Exception as e:
                logger.error("Briefing nudge failed for user %s: %s", profile.user_id, e)

        await db.commit()


async def _create_nudge(db: AsyncSession, user_id: str, nudge_type: str,
                         title: str, body: str, action_url: str):
    """Create a nudge if one of same type doesn't already exist today."""
    today = date.today()
    existing = await db.execute(
        select(Nudge).where(
            Nudge.user_id == user_id,
            Nudge.nudge_type == nudge_type,
            Nudge.sent_at >= datetime(today.year, today.month, today.day),
        )
    )
    if existing.scalar_one_or_none():
        return  # Already sent today

    nudge = Nudge(
        user_id=user_id,
        nudge_type=nudge_type,
        title=title,
        body=body,
        channel="app",
        action_url=action_url,
    )
    db.add(nudge)
