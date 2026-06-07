"""add_compliance_and_ledger

Revision ID: e3937218d940
Revises: ce1b119cf0fd
Create Date: 2026-06-07 20:45:21.688827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3937218d940'
down_revision: Union[str, Sequence[str], None] = 'ce1b119cf0fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
