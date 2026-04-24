"""CREDA production upgrade — profile fields, fund tables, assumptions, benchmarks.

Revision ID: 20260424_01
Revises:
Create Date: 2026-04-24

Idempotent: safe if tables/columns already exist (e.g. partial run or DB created out-of-band).
"""
from alembic import op
import sqlalchemy as sa


revision = "20260424_01"
down_revision = None
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _insp().has_table(name)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _insp().get_columns(table)}


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(ix.get("name") == index_name for ix in _insp().get_indexes(table))


def upgrade() -> None:
    # --- user_profiles columns ---
    _add_col = lambda col, *args, **kw: (
        op.add_column("user_profiles", sa.Column(col, *args, **kw))
        if not _has_column("user_profiles", col)
        else None
    )
    _add_col("completeness_pct", sa.Float(), server_default="0", nullable=True)
    _add_col("cams_uploaded", sa.Boolean(), server_default="false", nullable=True)
    _add_col("is_metro", sa.Boolean(), server_default="false", nullable=True)
    _add_col("risk_tolerance", sa.String(length=20), nullable=True)
    _add_col("basic_salary", sa.Float(), server_default="0", nullable=True)
    _add_col("rent_paid", sa.Float(), server_default="0", nullable=True)
    _add_col("has_nps", sa.Boolean(), server_default="false", nullable=True)
    _add_col("self_health_premium", sa.Float(), server_default="0", nullable=True)
    _add_col("parents_health_premium", sa.Float(), server_default="0", nullable=True)
    _add_col("parents_age_above_60", sa.Boolean(), server_default="false", nullable=True)
    _add_col("section_80c_amount", sa.Float(), server_default="0", nullable=True)
    _add_col("lta_amount", sa.Float(), server_default="0", nullable=True)
    _add_col("primary_goal", sa.String(length=50), nullable=True)
    _add_col("goal_target_amount", sa.Float(), server_default="0", nullable=True)
    _add_col("goal_target_years", sa.Integer(), server_default="0", nullable=True)
    _add_col("monthly_fixed_expenses", sa.Float(), server_default="0", nullable=True)
    _add_col("monthly_variable_expenses", sa.Float(), server_default="0", nullable=True)

    if _has_table("portfolio_funds") and not _has_column("portfolio_funds", "isin"):
        op.add_column(
            "portfolio_funds",
            sa.Column("isin", sa.String(length=20), server_default="", nullable=True),
        )

    if not _has_table("fund_nav"):
        op.create_table(
            "fund_nav",
            sa.Column("isin", sa.String(length=20), nullable=False),
            sa.Column("scheme_name", sa.Text(), nullable=True),
            sa.Column("nav", sa.Float(), nullable=True),
            sa.Column("nav_date", sa.Date(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
            sa.PrimaryKeyConstraint("isin"),
        )

    if not _has_table("fund_ter"):
        op.create_table(
            "fund_ter",
            sa.Column("isin", sa.String(length=20), nullable=False),
            sa.Column("scheme_name", sa.Text(), nullable=True),
            sa.Column("ter", sa.Float(), nullable=True),
            sa.Column("plan_type", sa.String(length=10), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
            sa.PrimaryKeyConstraint("isin"),
        )

    if not _has_table("fund_holdings"):
        op.create_table(
            "fund_holdings",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("fund_isin", sa.String(length=20), nullable=False),
            sa.Column("holding_isin", sa.String(length=20), nullable=False),
            sa.Column("holding_name", sa.Text(), nullable=True),
            sa.Column("weight", sa.Float(), nullable=True),
            sa.Column("month", sa.Date(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("fund_isin", "holding_isin", "month", name="uq_fund_holdings_key"),
        )

    if _has_table("fund_holdings") and not _has_index("fund_holdings", "ix_fund_holdings_fund_isin"):
        op.create_index(
            op.f("ix_fund_holdings_fund_isin"), "fund_holdings", ["fund_isin"], unique=False
        )

    if not _has_table("benchmark_returns"):
        op.create_table(
            "benchmark_returns",
            sa.Column("ticker", sa.String(length=40), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=True),
            sa.Column("cagr_1y", sa.Float(), nullable=True),
            sa.Column("cagr_3y", sa.Float(), nullable=True),
            sa.Column("cagr_5y", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
            sa.PrimaryKeyConstraint("ticker"),
        )

    if not _has_table("user_assumptions"):
        op.create_table(
            "user_assumptions",
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("inflation_rate", sa.Float(), server_default="0.06", nullable=True),
            sa.Column("equity_lc_return", sa.Float(), server_default="0.12", nullable=True),
            sa.Column("equity_mc_return", sa.Float(), server_default="0.14", nullable=True),
            sa.Column("equity_sc_return", sa.Float(), server_default="0.16", nullable=True),
            sa.Column("debt_return", sa.Float(), server_default="0.07", nullable=True),
            sa.Column("sip_stepup_pct", sa.Float(), server_default="0.10", nullable=True),
            sa.Column("stress_scenarios", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id"),
        )


def downgrade() -> None:
    if _has_table("user_assumptions"):
        op.drop_table("user_assumptions")
    if _has_table("benchmark_returns"):
        op.drop_table("benchmark_returns")
    if _has_index("fund_holdings", "ix_fund_holdings_fund_isin"):
        op.drop_index(op.f("ix_fund_holdings_fund_isin"), table_name="fund_holdings")
    if _has_table("fund_holdings"):
        op.drop_table("fund_holdings")
    if _has_table("fund_ter"):
        op.drop_table("fund_ter")
    if _has_table("fund_nav"):
        op.drop_table("fund_nav")

    if _has_column("portfolio_funds", "isin"):
        op.drop_column("portfolio_funds", "isin")

    for col in (
        "monthly_variable_expenses",
        "monthly_fixed_expenses",
        "goal_target_years",
        "goal_target_amount",
        "primary_goal",
        "lta_amount",
        "section_80c_amount",
        "parents_age_above_60",
        "parents_health_premium",
        "self_health_premium",
        "has_nps",
        "rent_paid",
        "basic_salary",
        "risk_tolerance",
        "is_metro",
        "cams_uploaded",
        "completeness_pct",
    ):
        if _has_column("user_profiles", col):
            op.drop_column("user_profiles", col)
