"""Add partner_monthly_expenses and other UserProfile columns missing from prior revisions.

These fields exist on the SQLAlchemy model; without this migration, SELECT on user_profiles
fails after `partner_monthly_income` was added in 20260424_02.

Idempotent: skips ADD if the column already exists.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260425_02"
down_revision: Union[str, None] = "20260425_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    cols = {c["name"] for c in insp.get_columns(table, schema=None)}
    return column in cols


def upgrade() -> None:
    if not _has_column("user_profiles", "partner_monthly_expenses"):
        op.add_column(
            "user_profiles",
            sa.Column("partner_monthly_expenses", sa.Float(), nullable=True),
        )
    if not _has_column("user_profiles", "partner_name"):
        op.add_column(
            "user_profiles",
            sa.Column("partner_name", sa.String(length=120), nullable=True, server_default=""),
        )
    if not _has_column("user_profiles", "partner_section_80c"):
        op.add_column(
            "user_profiles",
            sa.Column("partner_section_80c", sa.Float(), nullable=True, server_default="0"),
        )
    if not _has_column("user_profiles", "partner_nps_contribution"):
        op.add_column(
            "user_profiles",
            sa.Column("partner_nps_contribution", sa.Float(), nullable=True, server_default="0"),
        )
    if not _has_column("user_profiles", "partner_tax_bracket"):
        op.add_column(
            "user_profiles",
            sa.Column("partner_tax_bracket", sa.String(length=10), nullable=True, server_default=""),
        )
    if not _has_column("user_profiles", "monthly_sip_contribution"):
        op.add_column(
            "user_profiles",
            sa.Column("monthly_sip_contribution", sa.Float(), nullable=True, server_default="0"),
        )
    if not _has_column("user_profiles", "whatsapp_phone"):
        op.add_column(
            "user_profiles",
            sa.Column("whatsapp_phone", sa.String(length=20), nullable=True),
        )


def downgrade() -> None:
    for col in (
        "whatsapp_phone",
        "monthly_sip_contribution",
        "partner_tax_bracket",
        "partner_nps_contribution",
        "partner_section_80c",
        "partner_name",
        "partner_monthly_expenses",
    ):
        if _has_column("user_profiles", col):
            op.drop_column("user_profiles", col)
