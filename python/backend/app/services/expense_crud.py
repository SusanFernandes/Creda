"""Shared expense persistence (used by /budget/expense and /expenses)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Budget, Expense


async def create_logged_expense(
    db: AsyncSession,
    user_id: str,
    *,
    category: str,
    amount: float,
    description: str = "",
    expense_date: date | None = None,
    payment_method: str = "",
    is_recurring: bool = False,
) -> Expense:
    """Insert expense row and refresh Budget.actual_amount when a matching budget exists."""
    when = expense_date or date.today()
    cat = (category or "General").strip()[:100]
    if amount <= 0:
        raise ValueError("amount must be positive")

    expense = Expense(
        user_id=user_id,
        category=cat,
        amount=float(amount),
        description=(description or "")[:500],
        expense_date=when,
        payment_method=payment_method or "",
        is_recurring=is_recurring,
    )
    db.add(expense)
    await db.commit()

    month = when.strftime("%Y-%m")
    result = await db.execute(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.category == cat,
        )
    )
    budget = result.scalars().first()
    if budget:
        actual_sum = (await db.execute(
            select(func.sum(Expense.amount)).where(
                Expense.user_id == user_id,
                Expense.category == cat,
                func.to_char(Expense.expense_date, "YYYY-MM") == month,
            )
        )).scalar() or 0
        budget.actual_amount = float(actual_sum)
        await db.commit()

    await db.refresh(expense)
    return expense
