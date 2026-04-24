"""Add partner_monthly_income for couples finance field requests.

Revision ID: 20260424_02
Revises: 20260424_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20260424_02"
down_revision = "20260424_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("user_profiles"):
        return
    names = {c["name"] for c in insp.get_columns("user_profiles")}
    if "partner_monthly_income" not in names:
        op.add_column(
            "user_profiles",
            sa.Column("partner_monthly_income", sa.Float(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("user_profiles") and "partner_monthly_income" in {
        c["name"] for c in insp.get_columns("user_profiles")
    }:
        op.drop_column("user_profiles", "partner_monthly_income")
