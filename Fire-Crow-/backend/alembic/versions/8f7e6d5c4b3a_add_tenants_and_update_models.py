"""add_tenants_and_update_models

Revision ID: 8f7e6d5c4b3a
Revises: b9c8d7e6f5a4
Create Date: 2026-06-29 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "8f7e6d5c4b3a"
down_revision: Union[str, Sequence[str], None] = "b9c8d7e6f5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    from app.models import Base
    from app.models.tenant import Tenant

    required_tables = [
        Base.metadata.tables["tenants"],
    ]
    Base.metadata.create_all(bind=bind, tables=required_tables, checkfirst=True)


def downgrade() -> None:
    op.drop_table("tenants", if_exists=True)
