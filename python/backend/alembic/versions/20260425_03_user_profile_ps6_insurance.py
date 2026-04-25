"""Placeholder: PS6 / insurance-related profile columns (idempotent no-op if already applied)."""
from typing import Sequence, Union

revision: str = "20260425_03"
down_revision: Union[str, None] = "20260425_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
