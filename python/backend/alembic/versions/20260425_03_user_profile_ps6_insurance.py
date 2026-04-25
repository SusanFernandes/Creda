"""UserProfile: PS6 radar fields, insurance covers, emergency_fund_amount, annual_bonus."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260425_03"
down_revision: Union[str, None] = "20260425_02"
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
    text_empty = sa.text("''")
    cols: list[tuple[str, sa.types.TypeEngine, object]] = [
        ("watchlist_stocks", sa.Text(), text_empty),
        ("sector_interests", sa.Text(), text_empty),
        ("alert_types", sa.Text(), text_empty),
        ("term_insurance_cover", sa.Float(), sa.text("0")),
        ("health_insurance_cover", sa.Float(), sa.text("0")),
        ("emergency_fund_amount", sa.Float(), sa.text("0")),
        ("annual_bonus", sa.Float(), sa.text("0")),
    ]
    for name, coltype, server_default in cols:
        if not _has_column("user_profiles", name):
            op.add_column(
                "user_profiles",
                sa.Column(
                    name,
                    coltype,
                    nullable=False,
                    server_default=server_default,
                ),
            )


def downgrade() -> None:
    for name, _, _ in [
        ("annual_bonus", None, None),
        ("emergency_fund_amount", None, None),
        ("health_insurance_cover", None, None),
        ("term_insurance_cover", None, None),
        ("alert_types", None, None),
        ("sector_interests", None, None),
        ("watchlist_stocks", None, None),
    ]:
        if _has_column("user_profiles", name):
            op.drop_column("user_profiles", name)
