"""
Budget router — CRUD for monthly budgets and expense tracking.
"""
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import Budget, Expense

router = APIRouter(prefix="/budget", tags=["budget"])


class BudgetItemCreate(BaseModel):
    category: str
    planned_amount: float
    month: str = ""  # "2025-01" — defaults to current month


class ExpenseCreate(BaseModel):
    category: str
    amount: float
    description: str = ""
    expense_date: str = ""  # ISO format
    payment_method: str = ""
    is_recurring: bool = False


@router.post("/plan")
async def create_budget_item(
    body: BudgetItemCreate,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a budget category for a month."""
    month = body.month or datetime.now().strftime("%Y-%m")

    # Check if exists
    result = await db.execute(
        select(Budget).where(
            Budget.user_id == auth.user_id,
            Budget.month == month,
            Budget.category == body.category,
        )
    )
    existing = result.scalars().first()

    if existing:
        existing.planned_amount = body.planned_amount
    else:
        db.add(Budget(
            user_id=auth.user_id,
            month=month,
            category=body.category,
            planned_amount=body.planned_amount,
        ))

    await db.commit()
    return {"status": "ok", "month": month, "category": body.category}


@router.post("/expense")
async def log_expense(
    body: ExpenseCreate,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Log an actual expense."""
    from app.services.expense_crud import create_logged_expense

    expense_date = date.fromisoformat(body.expense_date) if body.expense_date else date.today()
    try:
        expense = await create_logged_expense(
            db,
            auth.user_id,
            category=body.category,
            amount=body.amount,
            description=body.description,
            expense_date=expense_date,
            payment_method=body.payment_method,
            is_recurring=body.is_recurring,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok", "expense_id": expense.id}


@router.delete("/expense/{expense_id}")
async def delete_expense(
    expense_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove a logged expense (owner only). Updates budget actual if a budget row exists."""
    result = await db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.user_id == auth.user_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")

    month = row.expense_date.strftime("%Y-%m")
    category = row.category
    await db.execute(delete(Expense).where(Expense.id == expense_id, Expense.user_id == auth.user_id))
    await db.commit()

    bud_result = await db.execute(
        select(Budget).where(
            Budget.user_id == auth.user_id,
            Budget.month == month,
            Budget.category == category,
        )
    )
    budget = bud_result.scalars().first()
    if budget:
        actual_sum = (await db.execute(
            select(func.sum(Expense.amount)).where(
                Expense.user_id == auth.user_id,
                Expense.category == category,
                func.to_char(Expense.expense_date, "YYYY-MM") == month,
            )
        )).scalar() or 0
        budget.actual_amount = float(actual_sum)
        await db.commit()

    return {"status": "ok", "deleted": expense_id}


@router.get("/summary")
async def budget_summary(
    month: str = Query("", description="YYYY-MM format"),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get budget vs actual for a month."""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    # Get all budget items
    budgets = await db.execute(
        select(Budget).where(
            Budget.user_id == auth.user_id,
            Budget.month == month,
        )
    )

    categories = []
    total_planned = 0
    total_actual = 0

    for b in budgets.scalars():
        # Get actual expenses for this category/month
        actual_sum = (await db.execute(
            select(func.sum(Expense.amount)).where(
                Expense.user_id == auth.user_id,
                Expense.category == b.category,
                func.to_char(Expense.expense_date, 'YYYY-MM') == month,
            )
        )).scalar() or 0

        pct = (actual_sum / b.planned_amount * 100) if b.planned_amount > 0 else 0
        categories.append({
            "category": b.category,
            "planned": b.planned_amount,
            "actual": actual_sum,
            "pct": round(pct, 1),
            "status": "over" if actual_sum > b.planned_amount else "under",
        })
        total_planned += b.planned_amount
        total_actual += actual_sum

    return {
        "month": month,
        "total_planned": total_planned,
        "total_actual": total_actual,
        "categories": categories,
        "savings": total_planned - total_actual,
    }


@router.get("/expenses")
async def list_expenses(
    month: str = Query("", description="YYYY-MM format"),
    category: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """List recent expenses."""
    query = select(Expense).where(
        Expense.user_id == auth.user_id,
    ).order_by(Expense.expense_date.desc()).limit(limit)

    if month:
        query = query.where(func.to_char(Expense.expense_date, 'YYYY-MM') == month)
    if category:
        query = query.where(Expense.category == category)

    result = await db.execute(query)
    return [
        {
            "id": e.id,
            "category": e.category,
            "amount": e.amount,
            "description": e.description,
            "expense_date": e.expense_date.isoformat() if e.expense_date else "",
            "payment_method": e.payment_method,
            "is_recurring": e.is_recurring,
        }
        for e in result.scalars()
    ]
