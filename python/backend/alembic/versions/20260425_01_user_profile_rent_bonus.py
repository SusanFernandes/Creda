"""Add rent_paid and ytd_bonus_income to user_profiles.

Idempotent: skips ADD if columns already exist (e.g. table was altered by create_all
or manual SQL before this revision was applied).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260425_01"
down_revision: Union[str, None] = "20260424_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table, schema=None)}
    return column in cols


def upgrade() -> None:
    if not _has_column("user_profiles", "rent_paid"):
        op.add_column(
            "user_profiles",
            sa.Column("rent_paid", sa.Float(), nullable=True, server_default="0"),
        )
    if not _has_column("user_profiles", "ytd_bonus_income"):
        op.add_column(
            "user_profiles",
            sa.Column("ytd_bonus_income", sa.Float(), nullable=True, server_default="0"),
        )


def downgrade() -> None:
    if _has_column("user_profiles", "ytd_bonus_income"):
        op.drop_column("user_profiles", "ytd_bonus_income")
    if _has_column("user_profiles", "rent_paid"):
        op.drop_column("user_profiles", "rent_paid")
