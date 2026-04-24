"""No-op baseline so DBs that reference revision 20260424_02 match the script tree.
Tables are still ensured by Base.metadata.create_all in app startup."""
from typing import Sequence, Union

revision: str = "20260424_02"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
