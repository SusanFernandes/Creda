"""UserProfile.notification_prefs JSON text for Settings → Notifications tab."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260425_04"
down_revision: Union[str, None] = "20260425_03"
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
    if not _has_column("user_profiles", "notification_prefs"):
        op.add_column(
            "user_profiles",
            sa.Column(
                "notification_prefs",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )


def downgrade() -> None:
    if _has_column("user_profiles", "notification_prefs"):
        op.drop_column("user_profiles", "notification_prefs")
