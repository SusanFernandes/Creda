"""Placeholder: partner / SIP / WhatsApp profile columns (idempotent no-op if already applied).

Restores revision chain for databases stamped at 20260425_04+ when this file was missing
from the tree. Safe on fresh DBs.
"""
from typing import Sequence, Union

revision: str = "20260425_02"
down_revision: Union[str, None] = "20260425_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
