"""add legal_hold column to audit_jobs

Revision ID: a1b2c3d4e5f6
Revises: f47ac10b58cc
Create Date: 2026-06-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f47ac10b58cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if _table_exists(inspector, "audit_jobs") and not _column_exists(inspector, "audit_jobs", "legal_hold"):
        op.add_column("audit_jobs", sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if _table_exists(inspector, "audit_jobs") and _column_exists(inspector, "audit_jobs", "legal_hold"):
        op.drop_column("audit_jobs", "legal_hold")
