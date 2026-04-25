"""Persist expenses from voice commands (same rules as /budget/expense)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Budget, Expense


async def apply_voice_expenses(
    db: AsyncSession,
    user_id: str,
    entries: list[dict],
) -> list[str]:
    """
    Insert expense rows and refresh Budget.actual_amount when a matching budget exists.
    Returns list of new expense ids.
    """
    ids: list[str] = []
    today = date.today()

    for e in entries:
        category = str(e.get("category") or "General").strip()[:100]
        amount = float(e.get("amount") or 0)
        if amount <= 0:
            continue
        description = str(e.get("description") or "")[:500]

        expense = Expense(
            user_id=user_id,
            category=category,
            amount=amount,
            description=description,
            expense_date=today,
            payment_method="",
            is_recurring=False,
        )
        db.add(expense)
        await db.flush()
        ids.append(expense.id)

        month = today.strftime("%Y-%m")
        result = await db.execute(
            select(Budget).where(
                Budget.user_id == user_id,
                Budget.month == month,
                Budget.category == category,
            )
        )
        budget = result.scalars().first()
        if budget:
            actual_sum = (await db.execute(
                select(func.sum(Expense.amount)).where(
                    Expense.user_id == user_id,
                    Expense.category == category,
                    func.to_char(Expense.expense_date, "YYYY-MM") == month,
                )
            )).scalar() or 0
            budget.actual_amount = float(actual_sum)

    if ids:
        await db.commit()
    return ids
