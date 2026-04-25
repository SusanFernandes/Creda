"""
Minimal expense API — for tools, webhooks, and integrations that only send category + amount.

Uses the same persistence as POST /budget/expense (JWT auth).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_expense_webhook_or_user
from app.database import get_db

router = APIRouter(tags=["expenses"])


@router.get(
    "/expenses",
    summary="Expense API usage",
)
async def expenses_usage():
    """Avoid 405 when probes hit GET; POST is required to create an expense."""
    return {
        "method": "POST",
        "body": {"category": "string", "amount": "number > 0"},
        "auth": "x-user-id from app proxy; or X-Webhook-Secret / Authorization Bearer matching "
        "WHATSAPP_EXPENSE_WEBHOOK_SECRET; or WHATSAPP_EXPENSE_TRUST_PUBLIC=true (no credentials, dev only).",
    }


class AddExpenseJSON(BaseModel):
    """Body for POST /expenses — only category and amount are required."""

    category: str = Field(..., min_length=1, max_length=100, description="Expense category, e.g. Food, Transport")
    amount: float = Field(..., gt=0, description="Amount in rupees (must be > 0)")

    @field_validator("category", mode="before")
    @classmethod
    def strip_category(cls, v: object) -> str:
        return str(v).strip() if v is not None else ""

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v: object) -> float:
        try:
            return float(v)
        except (TypeError, ValueError) as e:
            raise ValueError("amount must be a number") from e


@router.post(
    "/expenses",
    summary="Add expense (category + amount)",
    status_code=201,
    responses={201: {"description": "Expense created"}},
)
async def add_expense_minimal(
    body: AddExpenseJSON,
    auth: AuthContext = Depends(get_expense_webhook_or_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a logged expense for the authenticated user (or for the webhook user when
    X-Webhook-Secret is configured and matches).

    Same behaviour as `POST /budget/expense` with optional fields omitted (today's date, empty description).
    Send JSON: `{"category": "Food", "amount": 500}`.
    """
    from app.services.expense_crud import create_logged_expense

    if not body.category:
        raise HTTPException(status_code=400, detail="category is required")
    try:
        expense = await create_logged_expense(
            db,
            auth.user_id,
            category=body.category,
            amount=body.amount,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "status": "ok",
        "expense_id": expense.id,
        "category": expense.category,
        "amount": expense.amount,
    }
